# port from https://vulkan-tutorial.com/Drawing_a_triangle/Drawing/Rendering_and_presentation
# Python2 and PySide example.

from ctypes import (pythonapi, c_void_p, py_object)
import os

from vulkan import *
from PySide import (QtGui, QtCore)


pythonapi.PyCObject_AsVoidPtr.restype = c_void_p
pythonapi.PyCObject_AsVoidPtr.argtypes = [py_object]


WIDTH = 800
HEIGHT = 600

validationLayers = ["VK_LAYER_LUNARG_standard_validation"]
deviceExtensions = [VK_KHR_SWAPCHAIN_EXTENSION_NAME]

enableValidationLayers = True


def debugCallback(*args):
    print 'DEBUG: {} {}'.format(args[5], args[6])
    return 0

def createDebugReportCallbackEXT(instance, pCreateInfo, pAllocator):
    func = vkGetInstanceProcAddr(instance, 'vkCreateDebugReportCallbackEXT')
    if func:
        return func(instance, pCreateInfo, pAllocator)
    else:
        return VK_ERROR_EXTENSION_NOT_PRESENT

def destroyDebugReportCallbackEXT(instance, callback, pAllocator):
    func = vkGetInstanceProcAddr(instance, 'vkDestroyDebugReportCallbackEXT')
    if func:
        func(instance, callback, pAllocator)

def destroySurface(instance, surface, pAllocator=None):
    func = vkGetInstanceProcAddr(instance, 'vkDestroySurfaceKHR')
    if func:
        func(instance, surface, pAllocator)

def destroySwapChain(device, swapChain, pAllocator=None):
    func = vkGetDeviceProcAddr(device, 'vkDestroySwapchainKHR')
    if func:
        func(device, swapChain, pAllocator)


class Win32misc(object):
    @staticmethod
    def getInstance(hWnd):
        from cffi import FFI as _FFI
        _ffi = _FFI()
        _ffi.cdef('long __stdcall GetWindowLongA(void* hWnd, int nIndex);')
        _lib = _ffi.dlopen('User32.dll')
        return _lib.GetWindowLongA(_ffi.cast('void*', hWnd), -6)  # GWL_HINSTANCE


class QueueFamilyIndices(object):

    def __init__(self):
        self.graphicsFamily = -1
        self.presentFamily = -1

    def isComplete(self):
        return self.graphicsFamily >= 0 and self.presentFamily >= 0


class SwapChainSupportDetails(object):
    def __init__(self):
        self.capabilities = None
        self.formats = None
        self.presentModes = None

class HelloTriangleApplication(QtGui.QWidget):

    def __init__(self, parent=None):
        super(HelloTriangleApplication, self).__init__(parent)

        self.__instance = None
        self.__callback = None
        self.__surface = None
        self.__physicalDevice = None
        self.__device = None
        self.__graphicsQueue = None
        self.__presentQueue = None

        self.__swapChain = None
        self.__swapChainImages = None
        self.__swapChainImageFormat = None
        self.__swapChainExtent = None

        self.__swapChainImageViews = None
        self.__swapChainFramebuffers = None

        self.__renderPass = None
        self.__pipelineLayout = None
        self.__graphicsPipeline = None

        self.__commandPool = None
        self.__commandBuffers = None

        self.__imageAvailableSemaphore = None
        self.__renderFinishedSemaphore = None

    def __del__(self):
        vkDeviceWaitIdle(self.__device)

        if self.__imageAvailableSemaphore:
            vkDestroySemaphore(self.__device, self.__imageAvailableSemaphore, None)

        if self.__renderFinishedSemaphore:
            vkDestroySemaphore(self.__device, self.__renderFinishedSemaphore, None)

        if self.__commandBuffers:
            self.__commandBuffers = None

        if self.__commandPool:
            vkDestroyCommandPool(self.__device, self.__commandPool, None)

        if self.__swapChainFramebuffers:
            for i in self.__swapChainFramebuffers:
                vkDestroyFramebuffer(self.__device, i, None)
            self.__swapChainFramebuffers = None

        if self.__renderPass:
            vkDestroyRenderPass(self.__device, self.__renderPass, None)

        if self.__pipelineLayout:
            vkDestroyPipelineLayout(self.__device, self.__pipelineLayout, None)

        if self.__graphicsPipeline:
            vkDestroyPipeline(self.__device, self.__graphicsPipeline, None)

        if self.__swapChainImageViews:
            for i in self.__swapChainImageViews:
                vkDestroyImageView(self.__device, i, None)

        if self.__swapChain:
            destroySwapChain(self.__device, self.__swapChain, None)

        if self.__device:
            vkDestroyDevice(self.__device, None)

        if self.__surface:
            destroySurface(self.__instance, self.__surface, None)

        if self.__callback:
            destroyDebugReportCallbackEXT(self.__instance, self.__callback, None)

        if self.__instance:
            vkDestroyInstance(self.__instance, None)

    def __initWindow(self):
        self.setWindowTitle('Vulkan')
        self.setFixedSize(WIDTH, HEIGHT)
        self.createWinId()
        self.show()

    def __initVulkan(self):
        self.__createInstance()
        self.__setupDebugCallback()
        self.__createSurface()
        self.__pickPhysicalDevice()
        self.__createLogicalDevice()
        self.__createSwapChain()
        self.__createImageViews()
        self.__createRenderPass()
        self.__createGraphicsPipeline()
        self.__createFramebuffers()
        self.__createCommandPool()
        self.__createCommandBuffers()
        self.__createSemaphores()

    def timerEvent(self, event):
        self.__drawFrame()

        super(HelloTriangleApplication, self).timerEvent(event)

    def __createInstance(self):
        if enableValidationLayers and not self.__checkValidationLayerSupport():
            raise Exception("validation layers requested, but not available!")

        appInfo = VkApplicationInfo(
            pApplicationName='Hello Triangle',
            applicationVersion=VK_MAKE_VERSION(1, 0, 0),
            pEngineName='No Engine',
            engineVersion=VK_MAKE_VERSION(1, 0, 0),
            apiVersion=VK_MAKE_VERSION(1, 0, 3)
        )

        createInfo = VkInstanceCreateInfo(
            sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
            pApplicationInfo=appInfo
        )
        extensions = self.__getRequiredExtensions()
        ext = [ffi.new('char[]', i) for i in extensions]
        extArray = ffi.new('char*[]', ext)

        createInfo.enabledExtensionCount = len(extensions)
        createInfo.ppEnabledExtensionNames = extArray

        if enableValidationLayers:
            createInfo.enabledLayerCount = len(validationLayers)
            layers = [ffi.new('char[]', i) for i in validationLayers]
            vlayers = ffi.new('char*[]', layers)
            createInfo.ppEnabledLayerNames = vlayers
        else:
            createInfo.enabledLayerCount = 0

        self.__instance = vkCreateInstance(createInfo, None)

    def __setupDebugCallback(self):
        if not enableValidationLayers:
            return

        createInfo = VkDebugReportCallbackCreateInfoEXT(
            flags=VK_DEBUG_REPORT_ERROR_BIT_EXT | VK_DEBUG_REPORT_WARNING_BIT_EXT,
            pfnCallback=debugCallback
        )
        self.__callback = createDebugReportCallbackEXT(self.__instance, createInfo, None)
        if not self.__callback:
            raise Exception("failed to set up debug callback!")

    def __createSurface(self):
        vkCreateWin32SurfaceKHR = vkGetInstanceProcAddr(self.__instance, 'vkCreateWin32SurfaceKHR')

        hwnd = pythonapi.PyCObject_AsVoidPtr(self.winId())
        hinstance = Win32misc.getInstance(hwnd)
        createInfo = VkWin32SurfaceCreateInfoKHR(
            sType=VK_STRUCTURE_TYPE_WIN32_SURFACE_CREATE_INFO_KHR,
            hinstance=hinstance,
            hwnd=hwnd
        )
        self.__surface = vkCreateWin32SurfaceKHR(self.__instance, createInfo, None)
        if self.__surface is None:
            raise Exception("failed to create window surface!")

    def __pickPhysicalDevice(self):
        devices = vkEnumeratePhysicalDevices(self.__instance)

        for device in devices:
            if self.__isDeviceSuitable(device):
                self.__physicalDevice = device
                break

        if self.__physicalDevice is None:
            raise Exception("failed to find a suitable GPU!")

    def __createLogicalDevice(self):
        indices = self.__findQueueFamilies(self.__physicalDevice)
        uniqueQueueFamilies = {}.fromkeys((indices.graphicsFamily, indices.presentFamily))
        queueCreateInfos = []
        for queueFamily in uniqueQueueFamilies:
            queueCreateInfo = VkDeviceQueueCreateInfo(
                sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                queueFamilyIndex=queueFamily,
                queueCount=1,
                pQueuePriorities=[1.0]
            )
            queueCreateInfos.append(queueCreateInfo)

        deviceFeatures = VkPhysicalDeviceFeatures()
        deArray = [ffi.new('char[]', i) for i in deviceExtensions]
        deviceExtensions_c = ffi.new('char*[]', deArray)
        createInfo = VkDeviceCreateInfo(
            sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
            flags=0,
            pQueueCreateInfos=queueCreateInfos,
            queueCreateInfoCount=len(queueCreateInfos),
            pEnabledFeatures=[deviceFeatures],
            enabledExtensionCount=len(deviceExtensions),
            ppEnabledExtensionNames=deviceExtensions_c
        )

        if enableValidationLayers:
            createInfo.enabledLayerCount = len(validationLayers)
            layers = [ffi.new('char[]', i) for i in validationLayers]
            vlayers = ffi.new('char*[]', layers)
            createInfo.ppEnabledLayerNames = vlayers
        else:
            createInfo.enabledLayerCount = 0

        self.__device = vkCreateDevice(self.__physicalDevice, createInfo, None)
        if self.__device is None:
            raise Exception("failed to create logical device!")
        self.__graphicsQueue = vkGetDeviceQueue(self.__device, indices.graphicsFamily, 0)
        self.__presentQueue = vkGetDeviceQueue(self.__device, indices.presentFamily, 0)

    def __createSwapChain(self):
        swapChainSupport = self.__querySwapChainSupport(self.__physicalDevice)

        surfaceFormat = self.__chooseSwapSurfaceFormat(swapChainSupport.formats)
        presentMode = self.__chooseSwapPresentMode(swapChainSupport.presentModes)
        extent = self.__chooseSwapExtent(swapChainSupport.capabilities)

        imageCount = swapChainSupport.capabilities.minImageCount + 1
        if swapChainSupport.capabilities.maxImageCount > 0 and imageCount > swapChainSupport.capabilities.maxImageCount:
            imageCount = swapChainSupport.capabilities.maxImageCount

        createInfo = VkSwapchainCreateInfoKHR(
            sType=VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
            flags=0,
            surface=self.__surface,
            minImageCount=imageCount,
            imageFormat=surfaceFormat.format,
            imageColorSpace=surfaceFormat.colorSpace,
            imageExtent=extent,
            imageArrayLayers=1,
            imageUsage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT
        )

        indices = self.__findQueueFamilies(self.__physicalDevice)
        if indices.graphicsFamily != indices.presentFamily:
            createInfo.imageSharingMode = VK_SHARING_MODE_CONCURRENT
            createInfo.queueFamilyIndexCount = 2
            createInfo.pQueueFamilyIndices = [indices.graphicsFamily, indices.presentFamily]
        else:
            createInfo.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE

        createInfo.preTransform = swapChainSupport.capabilities.currentTransform
        createInfo.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR
        createInfo.presentMode = presentMode
        createInfo.clipped = True

        vkCreateSwapchainKHR = vkGetDeviceProcAddr(self.__device, 'vkCreateSwapchainKHR')
        self.__swapChain = vkCreateSwapchainKHR(self.__device, createInfo, None)

        vkGetSwapchainImagesKHR = vkGetDeviceProcAddr(self.__device, 'vkGetSwapchainImagesKHR')
        self.__swapChainImages = vkGetSwapchainImagesKHR(self.__device, self.__swapChain)

        self.__swapChainImageFormat = surfaceFormat.format
        self.__swapChainExtent = extent

    def __createImageViews(self):
        self.__swapChainImageViews = []
        components = VkComponentMapping(VK_COMPONENT_SWIZZLE_IDENTITY, VK_COMPONENT_SWIZZLE_IDENTITY,
                                        VK_COMPONENT_SWIZZLE_IDENTITY, VK_COMPONENT_SWIZZLE_IDENTITY)
        subresourceRange = VkImageSubresourceRange(VK_IMAGE_ASPECT_COLOR_BIT,
                                                   0, 1, 0, 1)
        for i, image in enumerate(self.__swapChainImages):
            createInfo = VkImageViewCreateInfo(
                sType=VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
                flags=0,
                image=image,
                viewType=VK_IMAGE_VIEW_TYPE_2D,
                format=self.__swapChainImageFormat,
                components=components,
                subresourceRange=subresourceRange
            )
            self.__swapChainImageViews.append(vkCreateImageView(self.__device, createInfo, None))

    def __createRenderPass(self):
        colorAttachment = VkAttachmentDescription(
            format=self.__swapChainImageFormat,
            samples=VK_SAMPLE_COUNT_1_BIT,
            loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR,
            storeOp=VK_ATTACHMENT_STORE_OP_STORE,
            stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE,
            stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE,
            initialLayout=VK_IMAGE_LAYOUT_UNDEFINED,
            finalLayout=VK_IMAGE_LAYOUT_PRESENT_SRC_KHR
        )

        colorAttachmentRef = VkAttachmentReference(
            attachment=0,
            layout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL
        )

        subPass = VkSubpassDescription(
            pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS,
            colorAttachmentCount=1,
            pColorAttachments=colorAttachmentRef
        )

        renderPassInfo = VkRenderPassCreateInfo(
            sType=VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
            attachmentCount=1,
            pAttachments=colorAttachment,
            subpassCount=1,
            pSubpasses=subPass
        )

        self.__renderPass = vkCreateRenderPass(self.__device, renderPassInfo, None)

    def __createGraphicsPipeline(self):
        path = os.path.dirname(os.path.abspath(__file__))
        vertShaderModule = self.__createShaderModule(os.path.join(path, 'hello_triangle_vert.spv'))
        fragShaderModule = self.__createShaderModule(os.path.join(path, 'hello_triangle_frag.spv'))


        vertShaderStageInfo = VkPipelineShaderStageCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
            flags=0,
            stage=VK_SHADER_STAGE_VERTEX_BIT,
            module=vertShaderModule,
            pName='main'
        )

        fragShaderStageInfo = VkPipelineShaderStageCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
            flags=0,
            stage=VK_SHADER_STAGE_FRAGMENT_BIT,
            module=fragShaderModule,
            pName='main'
        )

        shaderStages = [vertShaderStageInfo, fragShaderStageInfo]

        vertexInputInfo = VkPipelineVertexInputStateCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO,
            vertexBindingDescriptionCount=0,
            vertexAttributeDescriptionCount=0
        )

        inputAssembly = VkPipelineInputAssemblyStateCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
            topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
            primitiveRestartEnable=True
        )

        viewport = VkViewport(0.0, 0.0,
                              float(self.__swapChainExtent.width),
                              float(self.__swapChainExtent.height),
                              0.0, 1.0)
        scissor = VkRect2D([0, 0], self.__swapChainExtent)
        viewportState = VkPipelineViewportStateCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
            viewportCount=1,
            pViewports=viewport,
            scissorCount=1,
            pScissors=scissor
        )

        rasterizer = VkPipelineRasterizationStateCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
            depthClampEnable=False,
            rasterizerDiscardEnable=False,
            polygonMode=VK_POLYGON_MODE_FILL,
            lineWidth=1.0,
            cullMode=VK_CULL_MODE_BACK_BIT,
            frontFace=VK_FRONT_FACE_CLOCKWISE,
            depthBiasEnable=False
        )

        multisampling = VkPipelineMultisampleStateCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
            sampleShadingEnable=False,
            rasterizationSamples=VK_SAMPLE_COUNT_1_BIT
        )

        colorBlendAttachment = VkPipelineColorBlendAttachmentState(
            colorWriteMask=VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT | VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT,
            blendEnable=False
        )

        colorBlending = VkPipelineColorBlendStateCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
            logicOpEnable=False,
            logicOp=VK_LOGIC_OP_COPY,
            attachmentCount=1,
            pAttachments=colorBlendAttachment,
            blendConstants=[0.0, 0.0, 0.0, 0.0]
        )

        pipelineLayoutInfo = VkPipelineLayoutCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
            setLayoutCount=0,
            pushConstantRangeCount=0
        )

        self.__pipelineLayout = vkCreatePipelineLayout(self.__device, pipelineLayoutInfo, None)

        pipelineInfo = VkGraphicsPipelineCreateInfo(
            sType=VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
            stageCount=2,
            pStages=shaderStages,
            pVertexInputState=vertexInputInfo,
            pInputAssemblyState=inputAssembly,
            pViewportState=viewportState,
            pRasterizationState=rasterizer,
            pMultisampleState=multisampling,
            pColorBlendState=colorBlending,
            layout=self.__pipelineLayout,
            renderPass=self.__renderPass,
            subpass=0
        )

        self.__graphicsPipeline = vkCreateGraphicsPipelines(self.__device, VK_NULL_HANDLE, 1, pipelineInfo, None)

        vkDestroyShaderModule(self.__device, vertShaderModule, None)
        vkDestroyShaderModule(self.__device, fragShaderModule, None)

    def __createFramebuffers(self):
        self.__swapChainFramebuffers = []

        for imageView in self.__swapChainImageViews:
            attachments = [imageView,]

            framebufferInfo = VkFramebufferCreateInfo(
                sType=VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,
                renderPass=self.__renderPass,
                attachmentCount=1,
                pAttachments=attachments,
                width=self.__swapChainExtent.width,
                height=self.__swapChainExtent.height,
                layers=1
            )
            framebuffer = vkCreateFramebuffer(self.__device, framebufferInfo, None)
            self.__swapChainFramebuffers.append(framebuffer)

    def __createCommandPool(self):
        queueFamilyIndices = self.__findQueueFamilies(self.__physicalDevice)

        poolInfo = VkCommandPoolCreateInfo(
            sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
            queueFamilyIndex=queueFamilyIndices.graphicsFamily
        )

        self.__commandPool = vkCreateCommandPool(self.__device, poolInfo, None)

    def __createCommandBuffers(self):
        # self.__commandBuffers = []

        allocInfo = VkCommandBufferAllocateInfo(
            sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            commandPool=self.__commandPool,
            level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandBufferCount=len(self.__swapChainFramebuffers)
        )

        commandBuffers = vkAllocateCommandBuffers(self.__device, allocInfo)
        self.__commandBuffers = [ffi.addressof(commandBuffers, i)[0] for i in range(len(self.__swapChainFramebuffers))]

        for i, cmdBuffer in enumerate(self.__commandBuffers):
            beginInfo = VkCommandBufferBeginInfo(
                sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
                flags=VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT
            )

            vkBeginCommandBuffer(cmdBuffer, beginInfo)

            renderPassInfo = VkRenderPassBeginInfo(
                sType=VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
                renderPass=self.__renderPass,
                framebuffer=self.__swapChainFramebuffers[i],
                renderArea=[[0, 0], self.__swapChainExtent]
            )

            clearColor = VkClearValue([[0.0, 0.0, 0.0, 1.0]])
            renderPassInfo.clearValueCount = 1
            renderPassInfo.pClearValues = ffi.addressof(clearColor)

            vkCmdBeginRenderPass(cmdBuffer, renderPassInfo, VK_SUBPASS_CONTENTS_INLINE)

            vkCmdBindPipeline(cmdBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, self.__graphicsPipeline)
            vkCmdDraw(cmdBuffer, 3, 1, 0, 0)

            vkCmdEndRenderPass(cmdBuffer)

            vkEndCommandBuffer(cmdBuffer)

    def __createSemaphores(self):
        semaphoreInfo = VkSemaphoreCreateInfo(
            sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO
        )

        self.__imageAvailableSemaphore = vkCreateSemaphore(self.__device, semaphoreInfo, None)
        self.__renderFinishedSemaphore = vkCreateSemaphore(self.__device, semaphoreInfo, None)

    def __drawFrame(self):
        vkAcquireNextImageKHR = vkGetDeviceProcAddr(self.__device, 'vkAcquireNextImageKHR')
        vkQueuePresentKHR = vkGetDeviceProcAddr(self.__device, 'vkQueuePresentKHR')

        imageIndex = vkAcquireNextImageKHR(self.__device, self.__swapChain, 18446744073709551615,
                                           self.__imageAvailableSemaphore, VK_NULL_HANDLE)

        submitInfo = VkSubmitInfo(sType=VK_STRUCTURE_TYPE_SUBMIT_INFO)

        waitSemaphores = ffi.new('VkSemaphore[]', [self.__imageAvailableSemaphore])
        waitStages = ffi.new('uint32_t[]', [VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, ])
        submitInfo.waitSemaphoreCount = 1
        submitInfo.pWaitSemaphores = waitSemaphores
        submitInfo.pWaitDstStageMask = waitStages

        cmdBuffers = ffi.new('VkCommandBuffer[]', [self.__commandBuffers[imageIndex], ])
        submitInfo.commandBufferCount = 1
        submitInfo.pCommandBuffers = cmdBuffers

        signalSemaphores = ffi.new('VkSemaphore[]', [self.__renderFinishedSemaphore])
        submitInfo.signalSemaphoreCount = 1
        submitInfo.pSignalSemaphores = signalSemaphores

        vkQueueSubmit(self.__graphicsQueue, 1, submitInfo, VK_NULL_HANDLE)

        swapChains = [self.__swapChain]
        presentInfo = VkPresentInfoKHR(
            sType=VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
            waitSemaphoreCount=1,
            pWaitSemaphores=signalSemaphores,
            swapchainCount=1,
            pSwapchains=swapChains,
            pImageIndices=[imageIndex]
        )

        vkQueuePresentKHR(self.__presentQueue, presentInfo)

    def __createShaderModule(self, shaderFile):
        with open(shaderFile, 'rb') as sf:
            code = sf.read()
            codeSize = len(code)
            # c_code = ffi.new('unsigned char []', code)
            # pcode = ffi.cast('uint32_t*', c_code)

            createInfo = VkShaderModuleCreateInfo(
                sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
                codeSize=codeSize,
                pCode=code
            )

            return vkCreateShaderModule(self.__device, createInfo, None)


    def __chooseSwapSurfaceFormat(self, availableFormats):
        if len(availableFormats) == 1 and availableFormats[0].format == VK_FORMAT_UNDEFINED:
            return VkSurfaceFormatKHR(VK_FORMAT_B8G8R8A8_UNORM, 0)

        for availableFormat in availableFormats:
            if availableFormat.format == VK_FORMAT_B8G8R8A8_UNORM and availableFormat.colorSpace == 0:
                return availableFormat

        return availableFormats[0]

    def __chooseSwapPresentMode(self, availablePresentModes):
        for availablePresentMode in availablePresentModes:
            if availablePresentMode == VK_PRESENT_MODE_MAILBOX_KHR:
                return availablePresentMode

        return VK_PRESENT_MODE_FIFO_KHR

    def __chooseSwapExtent(self, capabilities):
        width = max(capabilities.minImageExtent.width, min(capabilities.maxImageExtent.width, WIDTH))
        height = max(capabilities.minImageExtent.height, min(capabilities.maxImageExtent.height, HEIGHT))
        return VkExtent2D(width, height)

    def __querySwapChainSupport(self, device):
        details = SwapChainSupportDetails()

        vkGetPhysicalDeviceSurfaceCapabilitiesKHR = vkGetInstanceProcAddr(self.__instance,
                                                                          'vkGetPhysicalDeviceSurfaceCapabilitiesKHR')
        details.capabilities = vkGetPhysicalDeviceSurfaceCapabilitiesKHR(device, self.__surface)

        vkGetPhysicalDeviceSurfaceFormatsKHR = vkGetInstanceProcAddr(self.__instance,
                                                                     'vkGetPhysicalDeviceSurfaceFormatsKHR')
        details.formats = vkGetPhysicalDeviceSurfaceFormatsKHR(device, self.__surface)

        vkGetPhysicalDeviceSurfacePresentModesKHR = vkGetInstanceProcAddr(self.__instance,
                                                                          'vkGetPhysicalDeviceSurfacePresentModesKHR')
        details.presentModes = vkGetPhysicalDeviceSurfacePresentModesKHR(device, self.__surface)

        return details

    def __isDeviceSuitable(self, device):
        indices = self.__findQueueFamilies(device)
        extensionsSupported = self.__checkDeviceExtensionSupport(device)
        swapChainAdequate = False
        if extensionsSupported:
            swapChainSupport = self.__querySwapChainSupport(device)
            swapChainAdequate = (not swapChainSupport.formats is None) and (not swapChainSupport.presentModes is None)
        return indices.isComplete() and extensionsSupported and swapChainAdequate

    def __checkDeviceExtensionSupport(self, device):
        availableExtensions = vkEnumerateDeviceExtensionProperties(device, None)

        for extension in availableExtensions:
            if extension.extensionName in deviceExtensions:
                return True

        return False

    def __findQueueFamilies(self, device):
        vkGetPhysicalDeviceSurfaceSupportKHR = vkGetInstanceProcAddr(self.__instance,
                                                                   'vkGetPhysicalDeviceSurfaceSupportKHR')
        indices = QueueFamilyIndices()

        queueFamilies = vkGetPhysicalDeviceQueueFamilyProperties(device)

        for i, queueFamily in enumerate(queueFamilies):
            if queueFamily.queueCount > 0 and queueFamily.queueFlags & VK_QUEUE_GRAPHICS_BIT:
                indices.graphicsFamily = i

            presentSupport = vkGetPhysicalDeviceSurfaceSupportKHR(device, i, self.__surface)

            if queueFamily.queueCount > 0 and presentSupport:
                indices.presentFamily = i

            if indices.isComplete():
                break

        return indices

    def __getRequiredExtensions(self):
        extensions = [i.extensionName for i in vkEnumerateInstanceExtensionProperties(None)]

        if enableValidationLayers:
            extensions.append(VK_EXT_DEBUG_REPORT_EXTENSION_NAME)

        return extensions

    def __checkValidationLayerSupport(self):
        availableLayers = vkEnumerateInstanceLayerProperties()

        for layerName in validationLayers:
            layerFound = False

            for layerProperties in availableLayers:

                if layerName == layerProperties.layerName:
                    layerFound = True
                    break
            if not layerFound:
                return False

        return True

    def run(self):
        self.__initWindow()
        self.__initVulkan()

        # self.__timer.start(30)
        self.startTimer(30)



if __name__ == '__main__':
    import sys

    app = QtGui.QApplication(sys.argv)

    win = HelloTriangleApplication()

    win.run()

    def cleanUp():
        global win
        del win

    app.aboutToQuit.connect(cleanUp)

    sys.exit(app.exec_())
