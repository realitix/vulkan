# port from https://github.com/Erkaman/vulkan_minimal_compute

import time
import math
import array

from vulkan import *
from PIL import Image
import numpy as np



WIDTH = 3200  # Size of rendered mandelbrot set.
HEIGHT = 2400  # Size of renderered mandelbrot set.
WORKGROUP_SIZE = 32  # Workgroup size in compute shader.


enableValidationLayers = True


class ComputeApplication(object):
    """The application launches a compute shader that renders the mandelbrot set,
    by rendering it into a storage buffer.
    The storage buffer is then read from the GPU, and saved as .png. """

    def __init__(self):
        # In order to use Vulkan, you must create an instance
        self.__instance = None
        self.__debugReportCallback = None

        # The physical device is some device on the system that supports usage of Vulkan.
        # Often, it is simply a graphics card that supports Vulkan.
        self.__physicalDevice = None

        # Then we have the logical device VkDevice, which basically allows
        # us to interact with the physical device.
        self.__device = None

        # The pipeline specifies the pipeline that all graphics and compute commands pass though in Vulkan.
        # We will be creating a simple compute pipeline in this application.
        self.__pipeline = None
        self.__pipelineLayout = None
        self.__computeShaderModule = None

        # The command buffer is used to record commands, that will be submitted to a queue.
        # To allocate such command buffers, we use a command pool.
        self.__commandPool = None
        self.__commandBuffer = None

        # Descriptors represent resources in shaders. They allow us to use things like
        # uniform buffers, storage buffers and images in GLSL.
        # A single descriptor represents a single resource, and several descriptors are organized
        # into descriptor sets, which are basically just collections of descriptors.
        self.__descriptorPool = None
        self.__descriptorSet = None
        self.__descriptorSetLayout = None

        # The mandelbrot set will be rendered to this buffer.
        # The memory that backs the buffer is bufferMemory.
        self.__buffer = None
        self.__bufferMemory = None

        # size of `buffer` in bytes.
        self.__bufferSize = 0

        self.__enabledLayers = []

        # In order to execute commands on a device(GPU), the commands must be submitted
        # to a queue. The commands are stored in a command buffer, and this command buffer
        # is given to the queue.
        # There will be different kinds of queues on the device. Not all queues support
        # graphics operations, for instance. For this application, we at least want a queue
        # that supports compute operations.

        # a queue supporting compute operations.
        self.__queue = None

        # Groups of queues that have the same capabilities(for instance, they all supports graphics and computer operations),
        # are grouped into queue families.

        # When submitting a command buffer, you must specify to which queue in the family you are submitting to.
        # This variable keeps track of the index of that queue in its family.
        self.__queueFamilyIndex = -1

        self.pixel = array.array('f', [0, 0, 0, 0])

        self.saveImageTime = 0
        self.cpuDataConverTime = 0

    def __del__(self):
        # Clean up all Vulkan Resources.

        if enableValidationLayers:
            # destroy callback.
            func = vkGetInstanceProcAddr(self.__instance, 'vkDestroyDebugReportCallbackEXT')
            if func == ffi.NULL:
                raise Exception("Could not load vkDestroyDebugReportCallbackEXT")
            if self.__debugReportCallback:
                func(self.__instance, self.__debugReportCallback, None)

        if self.__bufferMemory:
            vkFreeMemory(self.__device, self.__bufferMemory, None)
        if self.__buffer:
            vkDestroyBuffer(self.__device, self.__buffer, None)
        if self.__computeShaderModule:
            vkDestroyShaderModule(self.__device, self.__computeShaderModule, None)
        if self.__descriptorPool:
            vkDestroyDescriptorPool(self.__device, self.__descriptorPool, None)
        if self.__descriptorSetLayout:
            vkDestroyDescriptorSetLayout(self.__device, self.__descriptorSetLayout, None)
        if self.__pipelineLayout:
            vkDestroyPipelineLayout(self.__device, self.__pipelineLayout, None)
        if self.__pipeline:
            vkDestroyPipeline(self.__device, self.__pipeline, None)
        if self.__commandPool:
            vkDestroyCommandPool(self.__device, self.__commandPool, None)
        if self.__device:
            vkDestroyDevice(self.__device, None)
        if self.__instance:
            vkDestroyInstance(self.__instance, None)

    def run(self):
        # Buffer size of the storage buffer that will contain the rendered mandelbrot set.
        self.__bufferSize = self.pixel.buffer_info()[1] * self.pixel.itemsize * WIDTH * HEIGHT

        # Initialize vulkan
        self.createInstance()
        self.findPhysicalDevice()
        self.createDevice()
        self.createBuffer()
        self.createDescriptorSetLayout()
        self.createDescriptorSet()
        self.createComputePipeline()
        self.createCommandBuffer()

        # Finally, run the recorded command buffer.
        self.runCommandBuffer()

        # The former command rendered a mandelbrot set to a buffer.
        # Save that buffer as a png on disk.
        st = time.time()

        self.saveRenderedImage()

        self.saveImageTime = time.time() - st

    def saveRenderedImage(self):
        # Map the buffer memory, so that we can read from it on the CPU.
        pmappedMemory = vkMapMemory(self.__device, self.__bufferMemory, 0, self.__bufferSize, 0)

        # Get the color data from the buffer, and cast it to bytes.
        # We save the data to a vector.
        st = time.time()

        pa = np.frombuffer(pmappedMemory, np.float32)
        pa = pa.reshape((HEIGHT, WIDTH, 4))
        pa *= 255

        self.cpuDataConverTime = time.time() - st

        # Done reading, so unmap.
        vkUnmapMemory(self.__device, self.__bufferMemory)

        # Now we save the acquired color data to a .png.
        image = Image.fromarray(pa.astype(np.uint8))
        image.save('mandelbrot.png')

    @staticmethod
    def debugReportCallbackFn(*args):
        print('Debug Report: {} {}'.format(args[5], args[6]))
        return 0

    def createInstance(self):
        enabledExtensions = []
        # By enabling validation layers, Vulkan will emit warnings if the API
        # is used incorrectly. We shall enable the layer VK_LAYER_LUNARG_standard_validation,
        # which is basically a collection of several useful validation layers.
        if enableValidationLayers:
            # We get all supported layers with vkEnumerateInstanceLayerProperties.
            layerProperties = vkEnumerateInstanceLayerProperties()

            # And then we simply check if VK_LAYER_LUNARG_standard_validation is among the supported layers.
            supportLayerNames = [prop.layerName for prop in layerProperties]
            if "VK_LAYER_LUNARG_standard_validation" not in supportLayerNames:
                raise Exception('Layer VK_LAYER_LUNARG_standard_validation not supported')
            self.__enabledLayers.append("VK_LAYER_LUNARG_standard_validation")

            # We need to enable an extension named VK_EXT_DEBUG_REPORT_EXTENSION_NAME,
            # in order to be able to print the warnings emitted by the validation layer.
            # So again, we just check if the extension is among the supported extensions.
            extensionProperties = vkEnumerateInstanceExtensionProperties(None)

            supportExtensions = [prop.extensionName for prop in extensionProperties]
            if VK_EXT_DEBUG_REPORT_EXTENSION_NAME not in supportExtensions:
                raise Exception('Extension VK_EXT_DEBUG_REPORT_EXTENSION_NAME not supported')
            enabledExtensions.append(VK_EXT_DEBUG_REPORT_EXTENSION_NAME)

        # Next, we actually create the instance.

        # Contains application info. This is actually not that important.
        # The only real important field is apiVersion.
        applicationInfo = VkApplicationInfo(
            sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,
            pApplicationName='Hello world app',
            applicationVersion=0,
            pEngineName='awesomeengine',
            engineVersion=0,
            apiVersion=VK_API_VERSION_1_0
        )

        createInfo = VkInstanceCreateInfo(
            sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
            flags=0,
            pApplicationInfo=applicationInfo,
            # Give our desired layers and extensions to vulkan.
            enabledLayerCount=len(self.__enabledLayers),
            ppEnabledLayerNames=self.__enabledLayers,
            enabledExtensionCount=len(enabledExtensions),
            ppEnabledExtensionNames=enabledExtensions
        )

        # Actually create the instance.
        # Having created the instance, we can actually start using vulkan.
        self.__instance = vkCreateInstance(createInfo, None)

        # Register a callback function for the extension VK_EXT_DEBUG_REPORT_EXTENSION_NAME, so that warnings
        # emitted from the validation layer are actually printed.
        if enableValidationLayers:
            createInfo = VkDebugReportCallbackCreateInfoEXT(
                sType=VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT,
                flags=VK_DEBUG_REPORT_ERROR_BIT_EXT | VK_DEBUG_REPORT_WARNING_BIT_EXT | VK_DEBUG_REPORT_PERFORMANCE_WARNING_BIT_EXT,
                pfnCallback=self.debugReportCallbackFn
            )

            # We have to explicitly load this function.
            vkCreateDebugReportCallbackEXT = vkGetInstanceProcAddr(self.__instance, 'vkCreateDebugReportCallbackEXT')
            if vkCreateDebugReportCallbackEXT == ffi.NULL:
                raise Exception('Could not load vkCreateDebugReportCallbackEXT')

            # Create and register callback.
            self.__debugReportCallback = vkCreateDebugReportCallbackEXT(self.__instance, createInfo, None)

    def findPhysicalDevice(self):
        # In this function, we find a physical device that can be used with Vulkan.
        # So, first we will list all physical devices on the system with vkEnumeratePhysicalDevices.
        devices = vkEnumeratePhysicalDevices(self.__instance)

        # Next, we choose a device that can be used for our purposes.
        # With VkPhysicalDeviceFeatures(), we can retrieve a fine-grained list of physical features supported by the device.
        # However, in this demo, we are simply launching a simple compute shader, and there are no
        # special physical features demanded for this task.
        # With VkPhysicalDeviceProperties(), we can obtain a list of physical device properties. Most importantly,
        # we obtain a list of physical device limitations. For this application, we launch a compute shader,
        # and the maximum size of the workgroups and total number of compute shader invocations is limited by the physical device,
        # and we should ensure that the limitations named maxComputeWorkGroupCount, maxComputeWorkGroupInvocations and
        # maxComputeWorkGroupSize are not exceeded by our application.  Moreover, we are using a storage buffer in the compute shader,
        # and we should ensure that it is not larger than the device can handle, by checking the limitation maxStorageBufferRange.
        # However, in our application, the workgroup size and total number of shader invocations is relatively small, and the storage buffer is
        # not that large, and thus a vast majority of devices will be able to handle it. This can be verified by looking at some devices at_
        # http://vulkan.gpuinfo.org/
        # Therefore, to keep things simple and clean, we will not perform any such checks here, and just pick the first physical
        # device in the list. But in a real and serious application, those limitations should certainly be taken into account.

        # just use the first one
        self.__physicalDevice = devices[0]

    # Returns the index of a queue family that supports compute operations.
    def getComputeQueueFamilyIndex(self):
        # Retrieve all queue families.
        queueFamilies = vkGetPhysicalDeviceQueueFamilyProperties(self.__physicalDevice)

        # Now find a family that supports compute.
        for i, props in enumerate(queueFamilies):
            if props.queueCount > 0 and props.queueFlags & VK_QUEUE_COMPUTE_BIT:
                # found a queue with compute. We're done!
                return i

        return -1

    def createDevice(self):
        # We create the logical device in this function.

        self.__queueFamilyIndex = self.getComputeQueueFamilyIndex()
        # When creating the device, we also specify what queues it has.
        queueCreateInfo = VkDeviceQueueCreateInfo(
            sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
            queueFamilyIndex=self.__queueFamilyIndex,  # find queue family with compute capability.
            queueCount=1,  # create one queue in this family. We don't need more.
            pQueuePriorities=[1.0]  # we only have one queue, so this is not that imporant.
        )

        # Now we create the logical device. The logical device allows us to interact with the physical device.
        # Specify any desired device features here. We do not need any for this application, though.
        deviceFeatures = VkPhysicalDeviceFeatures()
        deviceCreateInfo = VkDeviceCreateInfo(
            sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
            enabledLayerCount=len(self.__enabledLayers),
            ppEnabledLayerNames=self.__enabledLayers,
            pQueueCreateInfos=queueCreateInfo,
            queueCreateInfoCount=1,
            pEnabledFeatures=deviceFeatures
        )

        self.__device = vkCreateDevice(self.__physicalDevice, deviceCreateInfo, None)
        self.__queue = vkGetDeviceQueue(self.__device, self.__queueFamilyIndex, 0)

    # find memory type with desired properties.
    def findMemoryType(self, memoryTypeBits, properties):
        memoryProperties = vkGetPhysicalDeviceMemoryProperties(self.__physicalDevice)

        # How does this search work?
        # See the documentation of VkPhysicalDeviceMemoryProperties for a detailed description.
        for i, mt in enumerate(memoryProperties.memoryTypes):
            if memoryTypeBits & (1 << i) and (mt.propertyFlags & properties) == properties:
                return i

        return -1

    def createBuffer(self):
        # We will now create a buffer. We will render the mandelbrot set into this buffer
        # in a computer shade later.
        bufferCreateInfo = VkBufferCreateInfo(
            sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,
            size=self.__bufferSize,  # buffer size in bytes.
            usage=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,  # buffer is used as a storage buffer.
            sharingMode=VK_SHARING_MODE_EXCLUSIVE  # buffer is exclusive to a single queue family at a time.
        )

        self.__buffer = vkCreateBuffer(self.__device, bufferCreateInfo, None)

        # But the buffer doesn't allocate memory for itself, so we must do that manually.

        # First, we find the memory requirements for the buffer.
        memoryRequirements = vkGetBufferMemoryRequirements(self.__device, self.__buffer)

        # There are several types of memory that can be allocated, and we must choose a memory type that:
        # 1) Satisfies the memory requirements(memoryRequirements.memoryTypeBits).
        # 2) Satifies our own usage requirements. We want to be able to read the buffer memory from the GPU to the CPU
        #    with vkMapMemory, so we set VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT.
        # Also, by setting VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, memory written by the device(GPU) will be easily
        # visible to the host(CPU), without having to call any extra flushing commands. So mainly for convenience, we set
        # this flag.
        index = self.findMemoryType(memoryRequirements.memoryTypeBits,
                                    VK_MEMORY_PROPERTY_HOST_COHERENT_BIT | VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)
        # Now use obtained memory requirements info to allocate the memory for the buffer.
        allocateInfo = VkMemoryAllocateInfo(
            sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
            allocationSize=memoryRequirements.size,  # specify required memory.
            memoryTypeIndex=index
        )

        # allocate memory on device.
        self.__bufferMemory = vkAllocateMemory(self.__device, allocateInfo, None)

        # Now associate that allocated memory with the buffer. With that, the buffer is backed by actual memory.
        vkBindBufferMemory(self.__device, self.__buffer, self.__bufferMemory, 0)

    def createDescriptorSetLayout(self):
        # Here we specify a descriptor set layout. This allows us to bind our descriptors to
        # resources in the shader.

        # Here we specify a binding of type VK_DESCRIPTOR_TYPE_STORAGE_BUFFER to the binding point
        # 0. This binds to
        #   layout(std140, binding = 0) buffer buf
        # in the compute shader.

        descriptorSetLayoutBinding = VkDescriptorSetLayoutBinding(
            binding=0,
            descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
            descriptorCount=1,
            stageFlags=VK_SHADER_STAGE_COMPUTE_BIT
        )

        descriptorSetLayoutCreateInfo = VkDescriptorSetLayoutCreateInfo(
            sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
            bindingCount=1,  # only a single binding in this descriptor set layout.
            pBindings=descriptorSetLayoutBinding
        )

        # Create the descriptor set layout.
        self.__descriptorSetLayout = vkCreateDescriptorSetLayout(self.__device, descriptorSetLayoutCreateInfo, None)

    def createDescriptorSet(self):
        # So we will allocate a descriptor set here.
        # But we need to first create a descriptor pool to do that.

        # Our descriptor pool can only allocate a single storage buffer.
        descriptorPoolSize = VkDescriptorPoolSize(
            type=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
            descriptorCount=1
        )

        descriptorPoolCreateInfo = VkDescriptorPoolCreateInfo(
            sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
            maxSets=1,  # we only need to allocate one descriptor set from the pool.
            poolSizeCount=1,
            pPoolSizes=descriptorPoolSize
        )

        # create descriptor pool.
        self.__descriptorPool = vkCreateDescriptorPool(self.__device, descriptorPoolCreateInfo, None)

        # With the pool allocated, we can now allocate the descriptor set.
        descriptorSetAllocateInfo = VkDescriptorSetAllocateInfo(
            sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
            descriptorPool=self.__descriptorPool,
            descriptorSetCount=1,
            pSetLayouts=[self.__descriptorSetLayout]
        )

        # allocate descriptor set.
        self.__descriptorSet = vkAllocateDescriptorSets(self.__device, descriptorSetAllocateInfo)[0]

        # Next, we need to connect our actual storage buffer with the descrptor.
        # We use vkUpdateDescriptorSets() to update the descriptor set.

        # Specify the buffer to bind to the descriptor.
        descriptorBufferInfo = VkDescriptorBufferInfo(
            buffer=self.__buffer,
            offset=0,
            range=self.__bufferSize
        )

        writeDescriptorSet = VkWriteDescriptorSet(
            sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            dstSet=self.__descriptorSet,
            dstBinding=0,  # write to the first, and only binding.
            descriptorCount=1,
            descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
            pBufferInfo=descriptorBufferInfo
        )

        # perform the update of the descriptor set.
        vkUpdateDescriptorSets(self.__device, 1, [writeDescriptorSet], 0, None)

    def createComputePipeline(self):
        # We create a compute pipeline here.

        # Create a shader module. A shader module basically just encapsulates some shader code.
        with open('mandelbrot_compute.spv', 'rb') as comp:
            code = comp.read()

            createInfo = VkShaderModuleCreateInfo(
                sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
                codeSize=len(code),
                pCode=code
            )

            self.__computeShaderModule = vkCreateShaderModule(self.__device, createInfo, None)

        # Now let us actually create the compute pipeline.
        # A compute pipeline is very simple compared to a graphics pipeline.
        # It only consists of a single stage with a compute shader.
        # So first we specify the compute shader stage, and it's entry point(main).
        shaderStageCreateInfo = VkPipelineShaderStageCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
            stage=VK_SHADER_STAGE_COMPUTE_BIT,
            module=self.__computeShaderModule,
            pName='main'
        )

        # The pipeline layout allows the pipeline to access descriptor sets.
        # So we just specify the descriptor set layout we created earlier.
        pipelineLayoutCreateInfo = VkPipelineLayoutCreateInfo(
            sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
            setLayoutCount=1,
            pSetLayouts=[self.__descriptorSetLayout]
        )
        self.__pipelineLayout = vkCreatePipelineLayout(self.__device, pipelineLayoutCreateInfo, None)

        pipelineCreateInfo = VkComputePipelineCreateInfo(
            sType=VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
            stage=shaderStageCreateInfo,
            layout=self.__pipelineLayout
        )

        # Now, we finally create the compute pipeline.
        pipelines = vkCreateComputePipelines(self.__device, VK_NULL_HANDLE, 1, pipelineCreateInfo, None)
        if len(pipelines) == 1:
            self.__pipeline = pipelines[0]
        else:
            raise Exception("Could not create compute pipeline")

    def createCommandBuffer(self):
        # We are getting closer to the end. In order to send commands to the device(GPU),
        # we must first record commands into a command buffer.
        # To allocate a command buffer, we must first create a command pool. So let us do that.
        commandPoolCreateInfo = VkCommandPoolCreateInfo(
            sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
            flags=0,
            # the queue family of this command pool. All command buffers allocated from this command pool,
            # must be submitted to queues of this family ONLY.
            queueFamilyIndex=self.__queueFamilyIndex
        )

        self.__commandPool = vkCreateCommandPool(self.__device, commandPoolCreateInfo, None)

        # Now allocate a command buffer from the command pool.
        commandBufferAllocateInfo = VkCommandBufferAllocateInfo(
            sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
            commandPool=self.__commandPool,
            # if the command buffer is primary, it can be directly submitted to queues.
            # A secondary buffer has to be called from some primary command buffer, and cannot be directly
            # submitted to a queue. To keep things simple, we use a primary command buffer.
            level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandBufferCount=1
        )

        self.__commandBuffer = vkAllocateCommandBuffers(self.__device, commandBufferAllocateInfo)[0]

        # Now we shall start recording commands into the newly allocated command buffer.
        beginInfo = VkCommandBufferBeginInfo(
            sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
            # the buffer is only submitted and used once in this application.
            flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT
        )
        vkBeginCommandBuffer(self.__commandBuffer, beginInfo)

        # We need to bind a pipeline, AND a descriptor set before we dispatch.
        # The validation layer will NOT give warnings if you forget these, so be very careful not to forget them.
        vkCmdBindPipeline(self.__commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, self.__pipeline)
        vkCmdBindDescriptorSets(self.__commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, self.__pipelineLayout,
                                0, 1, [self.__descriptorSet], 0, None)

        # Calling vkCmdDispatch basically starts the compute pipeline, and executes the compute shader.
        # The number of workgroups is specified in the arguments.
        # If you are already familiar with compute shaders from OpenGL, this should be nothing new to you.
        vkCmdDispatch(self.__commandBuffer,
                      int(math.ceil(WIDTH / float(WORKGROUP_SIZE))),  # int for py2 compatible
                      int(math.ceil(HEIGHT / float(WORKGROUP_SIZE))),  # int for py2 compatible
                      1)

        vkEndCommandBuffer(self.__commandBuffer)

    def runCommandBuffer(self):
        # Now we shall finally submit the recorded command buffer to a queue.
        submitInfo = VkSubmitInfo(
            sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,
            commandBufferCount=1,  # submit a single command buffer
            pCommandBuffers=[self.__commandBuffer]  # the command buffer to submit.
        )

        # We create a fence.
        fenceCreateInfo = VkFenceCreateInfo(
            sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO,
            flags=0
        )
        fence = vkCreateFence(self.__device, fenceCreateInfo, None)

        # We submit the command buffer on the queue, at the same time giving a fence.
        vkQueueSubmit(self.__queue, 1, submitInfo, fence)

        # The command will not have finished executing until the fence is signalled.
        # So we wait here.
        # We will directly after this read our buffer from the GPU,
        # and we will not be sure that the command has finished executing unless we wait for the fence.
        # Hence, we use a fence here.
        vkWaitForFences(self.__device, 1, [fence], VK_TRUE, 100000000000)

        vkDestroyFence(self.__device, fence, None)

if __name__ == '__main__':
    startTime = time.time()

    app = ComputeApplication()
    app.run()

    endTime = time.time()
    if enableValidationLayers:
        print('raw image data (CPU) convert time: {} seconds'.format(app.cpuDataConverTime))
        print('Vulkan setup and compute time: {} seconds'.format(endTime-startTime-app.saveImageTime))
        print('save image time: {} seconds'.format(app.saveImageTime))
        print('total time used: {} seconds'.format(endTime-startTime))

    del app
