# coding: utf-8

# flake8: noqa
import ctypes
import os
import sdl2
import sdl2.ext
import time
from vulkan import *


WIDTH = 400
HEIGHT = 400


# ----------
# Create instance
appInfo = VkApplicationInfo(
    sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,
    pApplicationName="Hello Triangle",
    applicationVersion=VK_MAKE_VERSION(1, 0, 0),
    pEngineName="No Engine",
    engineVersion=VK_MAKE_VERSION(1, 0, 0),
    apiVersion=VK_API_VERSION_1_0)

extensions = vkEnumerateInstanceExtensionProperties(None)
extensions = [e.extensionName for e in extensions]
print("availables extensions: %s\n" % extensions)

layers = vkEnumerateInstanceLayerProperties()
layers = [l.layerName for l in layers]
print("availables layers: %s\n" % layers)

layers = ['VK_LAYER_LUNARG_standard_validation']
extensions = ['VK_KHR_surface', 'VK_KHR_xlib_surface', 'VK_EXT_debug_report']
createInfo = VkInstanceCreateInfo(
    sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    flags=0,
    pApplicationInfo=appInfo,
    enabledExtensionCount=len(extensions),
    ppEnabledExtensionNames=extensions,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers)

instance = vkCreateInstance(pCreateInfo=createInfo)

# ----------
# Debug instance
vkCreateDebugReportCallbackEXT = vkGetInstanceProcAddr(
    instance,
    "vkCreateDebugReportCallbackEXT")
vkDestroyDebugReportCallbackEXT = vkGetInstanceProcAddr(
    instance,
    "vkDestroyDebugReportCallbackEXT")

def debugCallback(*args):
    print('DEBUG: ' + args[5] + ' ' + args[6])
    return 0

debug_create = VkDebugReportCallbackCreateInfoEXT(
    sType=VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT,
    flags=VK_DEBUG_REPORT_ERROR_BIT_EXT | VK_DEBUG_REPORT_WARNING_BIT_EXT,
    pfnCallback=debugCallback)
callback = vkCreateDebugReportCallbackEXT(instance=instance,
                                          pCreateInfo=debug_create)


# ----------
# Init sdl2
if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
    raise Exception(sdl2.SDL_GetError())

window = sdl2.SDL_CreateWindow(
    'test'.encode('ascii'),
    sdl2.SDL_WINDOWPOS_UNDEFINED,
    sdl2.SDL_WINDOWPOS_UNDEFINED, WIDTH, HEIGHT, 0)

if not window:
    raise Exception(sdl2.SDL_GetError())

wm_info = sdl2.SDL_SysWMinfo()
sdl2.SDL_VERSION(wm_info.version)
sdl2.SDL_GetWindowWMInfo(window, ctypes.byref(wm_info))


# ----------
# Create surface
vkDestroySurfaceKHR = vkGetInstanceProcAddr(instance, "vkDestroySurfaceKHR")

def surface_xlib():
    print("Create Xlib surface")
    vkCreateXlibSurfaceKHR = vkGetInstanceProcAddr(instance, "vkCreateXlibSurfaceKHR")
    surface_create = VkXlibSurfaceCreateInfoKHR(
        sType=VK_STRUCTURE_TYPE_XLIB_SURFACE_CREATE_INFO_KHR,
        dpy=wm_info.info.x11.display,
        window=wm_info.info.x11.window,
        flags=0)
    return vkCreateXlibSurfaceKHR(instance=instance, pCreateInfo=surface_create)

def surface_mir():
    print("Create mir surface")
    vkCreateMirSurfaceKHR = vkGetInstanceProcAddr(instance, "vkCreateMirSurfaceKHR")
    surface_create = VkMirSurfaceCreateInfoKHR(
        sType=VK_STRUCTURE_TYPE_MIR_SURFACE_CREATE_INFO_KHR,
        connection=wm_info.info.mir.connection,
        mirSurface=wm_info.info.mir.surface,
        flags=0)
    return vkCreateMirSurfaceKHR(instance=instance, pCreateInfo=surface_create)

def surface_wayland():
    print("Create wayland surface")
    vkCreateWaylandSurfaceKHR = vkGetInstanceProcAddr(instance, "vkCreateWaylandSurfaceKHR")
    surface_create = VkWaylandSurfaceCreateInfoKHR(
        sType=VK_STRUCTURE_TYPE_WAYLAND_SURFACE_CREATE_INFO_KHR,
        display=wm_info.info.wl.display,
        surface=wm_info.info.surface,
        flags=0)
    return vkCreateWaylandSurfaceKHR(instance=instance, pCreateInfo=surface_create)

def surface_win32():
    print("Create windows surface")
    vkCreateWin32SurfaceKHR = vkGetInstanceProcAddr(instance, "vkCreateWin32SurfaceKHR")
    surface_create = VkWin32SurfaceCreateInfoKHR(
        sType=VK_STRUCTURE_TYPE_WAYLAND_SURFACE_CREATE_INFO_KHR,
        hinstance='TODO',
        hwdn=wm_info.info.win.window,
        flags=0)
    return vkCreateWin32SurfaceKHR(instance=instance, pCreateInfo=surface_create)

surface_mapping = {
    sdl2.SDL_SYSWM_X11: surface_xlib}

surface = surface_mapping[wm_info.subsystem]()

# ----------
# Select physical device
physical_devices = vkEnumeratePhysicalDevices(instance)


physical_devices_features = {physical_device: vkGetPhysicalDeviceFeatures(physical_device)
                    for physical_device in physical_devices}
physical_devices_properties = {physical_device: vkGetPhysicalDeviceProperties(physical_device)
                      for physical_device in physical_devices}
physical_device = physical_devices[0]
print("availables devices: %s" % [p.deviceName
                                  for p in physical_devices_properties.values()])
print("selected device: %s\n" % physical_devices_properties[physical_device].deviceName)


# ----------
# Select queue family
vkGetPhysicalDeviceSurfaceSupportKHR = vkGetInstanceProcAddr(
    instance, 'vkGetPhysicalDeviceSurfaceSupportKHR')
queue_families = vkGetPhysicalDeviceQueueFamilyProperties(physicalDevice=physical_device)
print("%s available queue family" % len(queue_families))

queue_family_graphic_index = -1
queue_family_present_index = -1

for i, queue_family in enumerate(queue_families):
    support_present = vkGetPhysicalDeviceSurfaceSupportKHR(
        physicalDevice=physical_device,
        queueFamilyIndex=i,
        surface=surface)
    if (queue_family.queueCount > 0 and
       queue_family.queueFlags & VK_QUEUE_GRAPHICS_BIT):
        queue_family_graphic_index = i
    if queue_family.queueCount > 0 and support_present:
        queue_family_present_index = i

print("indice of selected queue families, graphic: %s, presentation: %s\n" % (
    queue_family_graphic_index, queue_family_present_index))


# ----------
# Create logical device and queues
extensions = vkEnumerateDeviceExtensionProperties(physicalDevice=physical_device, pLayerName=None)
extensions = [e.extensionName for e in extensions]
print("availables device extensions: %s\n" % extensions)

queues_create = [VkDeviceQueueCreateInfo(sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                                         queueFamilyIndex=i,
                                         queueCount=1,
                                         pQueuePriorities=[1],
                                         flags=0)
                 for i in {queue_family_graphic_index,
                           queue_family_present_index}]
device_create = VkDeviceCreateInfo(
    sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
    pQueueCreateInfos=queues_create,
    queueCreateInfoCount=len(queues_create),
    pEnabledFeatures=physical_devices_features[physical_device],
    flags=0,
    enabledLayerCount=len(layers),
    ppEnabledLayerNames=layers,
    enabledExtensionCount=len(extensions),
    ppEnabledExtensionNames=extensions
)

logical_device = vkCreateDevice(physicalDevice=physical_device,
                                pCreateInfo=device_create)
graphic_queue = vkGetDeviceQueue(
    device=logical_device,
    queueFamilyIndex=queue_family_graphic_index,
    queueIndex=0)
presentation_queue = vkGetDeviceQueue(
    device=logical_device,
    queueFamilyIndex=queue_family_present_index,
    queueIndex=0)
print("Logical device and graphic queue successfully created\n")


# ----------
# Create swapchain
vkGetPhysicalDeviceSurfaceCapabilitiesKHR = vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfaceCapabilitiesKHR")
vkGetPhysicalDeviceSurfaceFormatsKHR = vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfaceFormatsKHR")
vkGetPhysicalDeviceSurfacePresentModesKHR = vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceSurfacePresentModesKHR")

surface_capabilities = vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physicalDevice=physical_device, surface=surface)
surface_formats = vkGetPhysicalDeviceSurfaceFormatsKHR(physicalDevice=physical_device, surface=surface)
surface_present_modes = vkGetPhysicalDeviceSurfacePresentModesKHR(physicalDevice=physical_device, surface=surface)

if not surface_formats or not surface_present_modes:
    raise Exception('No available swapchain')

def get_surface_format(formats):
    for f in formats:
        if f.format == VK_FORMAT_UNDEFINED:
            return  f
        if (f.format == VK_FORMAT_B8G8R8A8_UNORM and
            f.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR):
            return f
    return formats[0]

def get_surface_present_mode(present_modes):
    for p in present_modes:
        if p == VK_PRESENT_MODE_MAILBOX_KHR:
            return p
    return VK_PRESENT_MODE_FIFO_KHR;

def get_swap_extent(capabilities):
    uint32_max = 4294967295
    if capabilities.currentExtent.width != uint32_max:
        return capabilities.currentExtent

    width = max(
        capabilities.minImageExtent.width,
        min(capabilities.maxImageExtent.width, WIDTH))
    height = max(
        capabilities.minImageExtent.height,
        min(capabilities.maxImageExtent.height, HEIGHT))
    actualExtent = VkExtent2D(width=width, height=height);
    return actualExtent


surface_format = get_surface_format(surface_formats)
present_mode = get_surface_present_mode(surface_present_modes)
extent = get_swap_extent(surface_capabilities)
imageCount = surface_capabilities.minImageCount + 1;
if surface_capabilities.maxImageCount > 0 and imageCount > surface_capabilities.maxImageCount:
    imageCount = surface_capabilities.maxImageCount

print('selected format: %s' % surface_format.format)
print('%s available swapchain present modes' % len(surface_present_modes))


imageSharingMode = VK_SHARING_MODE_EXCLUSIVE
queueFamilyIndexCount = 0
pQueueFamilyIndices = None

if queue_family_graphic_index != queue_family_present_index:
    imageSharingMode = VK_SHARING_MODE_CONCURREN
    queueFamilyIndexCount = 2
    pQueueFamilyIndices = queueFamilyIndices

vkCreateSwapchainKHR = vkGetInstanceProcAddr(instance, 'vkCreateSwapchainKHR')
vkDestroySwapchainKHR = vkGetInstanceProcAddr(instance, 'vkDestroySwapchainKHR')
vkGetSwapchainImagesKHR = vkGetInstanceProcAddr(instance, 'vkGetSwapchainImagesKHR')

swapchain_create = VkSwapchainCreateInfoKHR(
    sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
    flags=0,
    surface=surface,
    minImageCount=imageCount,
    imageFormat=surface_format.format,
    imageColorSpace=surface_format.colorSpace,
    imageExtent=extent,
    imageArrayLayers=1,
    imageUsage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
    imageSharingMode=imageSharingMode,
    queueFamilyIndexCount=queueFamilyIndexCount,
    pQueueFamilyIndices=pQueueFamilyIndices,
    compositeAlpha=VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
    presentMode=present_mode,
    clipped=VK_TRUE,
    oldSwapchain=None,
    preTransform=surface_capabilities.currentTransform)

swapchain = vkCreateSwapchainKHR(logical_device, swapchain_create)
swapchain_images = vkGetSwapchainImagesKHR(logical_device, swapchain)

# Create image view for each image in swapchain
image_views = []
for image in swapchain_images:
    subresourceRange = VkImageSubresourceRange(
        aspectMask=VK_IMAGE_ASPECT_COLOR_BIT,
        baseMipLevel=0,
        levelCount=1,
        baseArrayLayer=0,
        layerCount=1)

    components = VkComponentMapping(
        r=VK_COMPONENT_SWIZZLE_IDENTITY,
        g=VK_COMPONENT_SWIZZLE_IDENTITY,
        b=VK_COMPONENT_SWIZZLE_IDENTITY,
        a=VK_COMPONENT_SWIZZLE_IDENTITY)

    imageview_create = VkImageViewCreateInfo(
        sType=VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        image=image,
        flags=0,
        viewType=VK_IMAGE_VIEW_TYPE_2D,
        format=surface_format.format,
        components=components,
        subresourceRange=subresourceRange)

    image_views.append(vkCreateImageView(logical_device, imageview_create))


print("%s images view created" % len(image_views))

# Load spirv shader
path = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(path, "vert.spv"), 'rb') as f:
    vert_shader_spirv = f.read()
with open(os.path.join(path, "frag.spv"), 'rb') as f:
    frag_shader_spirv = f.read()

# Create shader
vert_shader_create = VkShaderModuleCreateInfo(
    sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
    flags=0,
    codeSize=len(vert_shader_spirv),
    pCode=vert_shader_spirv
)

vert_shader_module = vkCreateShaderModule(logical_device, vert_shader_create)

frag_shader_create = VkShaderModuleCreateInfo(
    sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
    flags=0,
    codeSize=len(frag_shader_spirv),
    pCode=frag_shader_spirv)

frag_shader_module = vkCreateShaderModule(logical_device, frag_shader_create)

# Create shader stage
vert_stage_create = VkPipelineShaderStageCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
    stage=VK_SHADER_STAGE_VERTEX_BIT,
    module=vert_shader_module,
    flags=0,
    pSpecializationInfo=None,
    pName='main')

frag_stage_create = VkPipelineShaderStageCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
    stage=VK_SHADER_STAGE_FRAGMENT_BIT,
    module=frag_shader_module,
    flags=0,
    pSpecializationInfo=None,
    pName='main')

# Create render pass
color_attachement = VkAttachmentDescription(
    flags=0,
    format=surface_format.format,
    samples=VK_SAMPLE_COUNT_1_BIT,
    loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR,
    storeOp=VK_ATTACHMENT_STORE_OP_STORE,
    stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE,
    stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE,
    initialLayout=VK_IMAGE_LAYOUT_UNDEFINED,
    finalLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR)

color_attachement_reference = VkAttachmentReference(
    attachment=0,
    layout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL)

sub_pass = VkSubpassDescription(
    flags=0,
    pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS,
    inputAttachmentCount=0,
    pInputAttachments=None,
    pResolveAttachments=None,
    pDepthStencilAttachment=None,
    preserveAttachmentCount=0,
    pPreserveAttachments=None,
    colorAttachmentCount=1,
    pColorAttachments=[color_attachement_reference])

dependency = VkSubpassDependency(
    dependencyFlags=0,
    srcSubpass=VK_SUBPASS_EXTERNAL,
    dstSubpass=0,
    srcStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
    srcAccessMask=0,
    dstStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
    dstAccessMask=VK_ACCESS_COLOR_ATTACHMENT_READ_BIT | VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT)

render_pass_create = VkRenderPassCreateInfo(
    flags=0,
    sType=VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
    attachmentCount=1,
    pAttachments=[color_attachement],
    subpassCount=1,
    pSubpasses=[sub_pass],
    dependencyCount=1,
    pDependencies=[dependency])

render_pass = vkCreateRenderPass(logical_device, render_pass_create)

# Create graphic pipeline
vertex_input_create = VkPipelineVertexInputStateCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO,
    flags=0,
    vertexBindingDescriptionCount=0,
    pVertexBindingDescriptions=None,
    vertexAttributeDescriptionCount=0,
    pVertexAttributeDescriptions=None)

input_assembly_create = VkPipelineInputAssemblyStateCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
    flags=0,
    topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
    primitiveRestartEnable=VK_FALSE)
viewport = VkViewport(
    x=0., y=0., width=float(extent.width), height=float(extent.height),
    minDepth=0., maxDepth=1.)

scissor_offset = VkOffset2D(x=0, y=0)
scissor = VkRect2D(offset=scissor_offset, extent=extent)
viewport_state_create = VkPipelineViewportStateCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
    flags=0,
    viewportCount=1,
    pViewports=[viewport],
    scissorCount=1,
    pScissors=[scissor])

rasterizer_create = VkPipelineRasterizationStateCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
    flags=0,
    depthClampEnable=VK_FALSE,
    rasterizerDiscardEnable=VK_FALSE,
    polygonMode=VK_POLYGON_MODE_FILL,
    lineWidth=1,
    cullMode=VK_CULL_MODE_BACK_BIT,
    frontFace=VK_FRONT_FACE_CLOCKWISE,
    depthBiasEnable=VK_FALSE,
    depthBiasConstantFactor=0.,
    depthBiasClamp=0.,
    depthBiasSlopeFactor=0.)

multisample_create = VkPipelineMultisampleStateCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
    flags=0,
    sampleShadingEnable=VK_FALSE,
    rasterizationSamples=VK_SAMPLE_COUNT_1_BIT,
    minSampleShading=1,
    pSampleMask=None,
    alphaToCoverageEnable=VK_FALSE,
    alphaToOneEnable=VK_FALSE)

color_blend_attachement = VkPipelineColorBlendAttachmentState(
    colorWriteMask=VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT | VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT,
    blendEnable=VK_FALSE,
    srcColorBlendFactor=VK_BLEND_FACTOR_ONE,
    dstColorBlendFactor=VK_BLEND_FACTOR_ZERO,
    colorBlendOp=VK_BLEND_OP_ADD,
    srcAlphaBlendFactor=VK_BLEND_FACTOR_ONE,
    dstAlphaBlendFactor=VK_BLEND_FACTOR_ZERO,
    alphaBlendOp=VK_BLEND_OP_ADD)

color_blend_create = VkPipelineColorBlendStateCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
    flags=0,
    logicOpEnable=VK_FALSE,
    logicOp=VK_LOGIC_OP_COPY,
    attachmentCount=1,
    pAttachments=[color_blend_attachement],
    blendConstants=[0, 0, 0, 0])

push_constant_ranges = VkPushConstantRange(
    stageFlags=0,
    offset=0,
    size=0)

pipeline_layout_create = VkPipelineLayoutCreateInfo(
    sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
    flags=0,
    setLayoutCount=0,
    pSetLayouts=None,
    pushConstantRangeCount=0,
    pPushConstantRanges=[push_constant_ranges])

pipeline_layout = vkCreatePipelineLayout(logical_device, pipeline_layout_create)

# Finally create graphic pipeline
pipeline_create = VkGraphicsPipelineCreateInfo(
    sType=VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
    flags=0,
    stageCount=2,
    pStages=[vert_stage_create, frag_stage_create],
    pVertexInputState=vertex_input_create,
    pInputAssemblyState=input_assembly_create,
    pTessellationState=None,
    pViewportState=viewport_state_create,
    pRasterizationState=rasterizer_create,
    pMultisampleState=multisample_create,
    pDepthStencilState=None,
    pColorBlendState=color_blend_create,
    pDynamicState=None,
    layout=pipeline_layout,
    renderPass=render_pass,
    subpass=0,
    basePipelineHandle=None,
    basePipelineIndex=-1)

pipeline = vkCreateGraphicsPipelines(logical_device, None, 1, [pipeline_create])


# Framebuffers creation
framebuffers = []
for image in image_views:
    attachments = [image]
    framebuffer_create = VkFramebufferCreateInfo(
        sType=VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
        flags=0,
        renderPass=render_pass,
        attachmentCount=len(attachments),
        pAttachments=attachments,
        width=extent.width,
        height=extent.height,
        layers=1)
    framebuffers.append(
        vkCreateFramebuffer(logical_device, framebuffer_create))

# Create command pools
command_pool_create = VkCommandPoolCreateInfo(
    sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
    queueFamilyIndex=queue_family_graphic_index,
    flags=0)

command_pool = vkCreateCommandPool(logical_device, command_pool_create)

# Create command buffers
command_buffers_create = VkCommandBufferAllocateInfo(
    sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
    commandPool=command_pool,
    level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,
    commandBufferCount=len(framebuffers))

command_buffers = vkAllocateCommandBuffers(logical_device, command_buffers_create)

# Record command buffer
for i, command_buffer in enumerate(command_buffers):
    command_buffer_begin_create = VkCommandBufferBeginInfo(
        sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
        flags=VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT,
        pInheritanceInfo=None)

    vkBeginCommandBuffer(command_buffer, command_buffer_begin_create)

    # Create render pass
    render_area = VkRect2D(offset=VkOffset2D(x=0, y=0),
                           extent=extent)
    color = VkClearColorValue(float32=[0, 1, 0, 1])
    clear_value = VkClearValue(color=color)

    render_pass_begin_create = VkRenderPassBeginInfo(
        sType=VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
        renderPass=render_pass,
        framebuffer=framebuffers[i],
        renderArea=render_area,
        clearValueCount=1,
        pClearValues=[clear_value])

    vkCmdBeginRenderPass(command_buffer, render_pass_begin_create, VK_SUBPASS_CONTENTS_INLINE)

    # Bing pipeline
    vkCmdBindPipeline(command_buffer, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline)

    # Draw
    vkCmdDraw(command_buffer, 3, 1, 0, 0)

    # End
    vkCmdEndRenderPass(command_buffer)
    vkEndCommandBuffer(command_buffer)

# Create semaphore
semaphore_create = VkSemaphoreCreateInfo(
    sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO,
    flags=0)
semaphore_image_available = vkCreateSemaphore(logical_device, semaphore_create)
semaphore_render_finished = vkCreateSemaphore(logical_device, semaphore_create)

vkAcquireNextImageKHR = vkGetInstanceProcAddr(instance, "vkAcquireNextImageKHR")
vkQueuePresentKHR = vkGetInstanceProcAddr(instance, "vkQueuePresentKHR")



wait_semaphores = [semaphore_image_available]
wait_stages = [VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT]
signal_semaphores = [semaphore_render_finished]

submit_create = VkSubmitInfo(
    sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,
    waitSemaphoreCount=len(wait_semaphores),
    pWaitSemaphores=wait_semaphores,
    pWaitDstStageMask=wait_stages,
    commandBufferCount=1,
    pCommandBuffers=[command_buffers[0]],
    signalSemaphoreCount=len(signal_semaphores),
    pSignalSemaphores=signal_semaphores)

present_create = VkPresentInfoKHR(
    sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
    waitSemaphoreCount=1,
    pWaitSemaphores=signal_semaphores,
    swapchainCount=1,
    pSwapchains=[swapchain],
    pImageIndices=[0],
    pResults=None)


# optimization to avoid creating a new array each time
submit_list = ffi.new('VkSubmitInfo[1]', [submit_create])


def draw_frame():
    try:
        image_index = vkAcquireNextImageKHR(logical_device, swapchain, UINT64_MAX, semaphore_image_available, None)
    except VkNotReady:
        print('not ready')
        return

    submit_create.pCommandBuffers[0] = command_buffers[image_index]
    vkQueueSubmit(graphic_queue, 1, submit_list, None)

    present_create.pImageIndices[0] = image_index
    vkQueuePresentKHR(presentation_queue, present_create)


# Main loop
running = True
if sys.version_info >= (3, 0):
    clock = time.perf_counter
else:
    clock = time.clock

#running = False
i = 0
last_time = clock() * 1000
fps = 0
while running:
    fps += 1
    if clock() * 1000 - last_time >= 1000:
        last_time = clock() * 1000
        print("FPS: %s" % fps)
        fps = 0

    events = sdl2.ext.get_events()
    draw_frame()
    for event in events:
        if event.type == sdl2.SDL_QUIT:
            running = False
            vkDeviceWaitIdle(logical_device)
            break


# ----------
# Clean everything
vkDestroySemaphore(logical_device, semaphore_image_available)
vkDestroySemaphore(logical_device, semaphore_render_finished)
vkDestroyCommandPool(logical_device, command_pool)
for f in framebuffers:
    vkDestroyFramebuffer(logical_device, f)
vkDestroyPipeline(logical_device, pipeline)
vkDestroyPipelineLayout(logical_device, pipeline_layout)
vkDestroyRenderPass(logical_device, render_pass)
vkDestroyShaderModule(logical_device, frag_shader_module)
vkDestroyShaderModule(logical_device, vert_shader_module)
for i in image_views:
    vkDestroyImageView(logical_device, i)
vkDestroySwapchainKHR(logical_device, swapchain)
vkDestroyDevice(logical_device)
vkDestroySurfaceKHR(instance, surface)
vkDestroyDebugReportCallbackEXT(instance, callback)
vkDestroyInstance(instance)
