现代系统大多提供DMA和中断重映射功能来确保I/O设备在有限的范围内运行，比如x86平台的AMD-Vi和Intel VT-d。VFIO（Virtual Function I/O）是一个可以将设备I/O、中断和DMA等能力安全的暴露到用户态空间，从而使用用户态驱动实现设备驱动的框架。通过VFIO进行设备直通到虚拟机，可以获得更高的设备I/O性能。

实现用户态驱动最关键的问题在于如何安全可控的将设备的DMA能力暴露到用户空间，IOMMU的出现可以限制设备对内存的访问，恶意的设备不能直接读写物理内存，经过IOMMU映射之后才能使用IOVA或者虚拟地址进行访存，由IOMMU来保证访存的安全性。

## VFIO内核组件

VFIO内核组件主要包括如下图所示，通过设备文件向用户态提供统一访问接口vfio interface层，包括:

* VFIO container
* VFIO group
* VFIO device

``` 
+-----------------------------------------+
|            vfio interface               |
+-----------------------------------------+
|  vfio_iommu_driver |       vfio_pci     |
+--------------------+--------------------+
|        iommu       |       pci_bus      |
+--------------------+--------------------+
```

vfio interface 封装了vfio_iommu_driver和vfio_pci分别和底层的IOMMU、PCI驱动进行交互，vfio_iommu_driver为VFIO提供了IOMMU重映射驱动，向用户态暴露DMA操作，主要是vfio_iommu_type1驱动，利用IOMMU管理IO页表的能力来进行IO重映射。vfio_pci模块封装pci设备驱动并和用户态程序进行配合完成用户态的设备配置模拟、Bar空间重定向及中断重映射等功能。

VFIO框架中比较重要的几个概念包括：Container、Group和Device，其相互之间的关系如图所示，一个container可以理解为实际的物理资源集合，每个container中可以有多个group，group描述了设备在物理上的划分，一个group可以有多个device，划分的逻辑取决于硬件上的IOMMU拓扑结构。

``` 
container
+------------------------+
|    group0    group1    |
|  +-------+  +------+   |
|  | dev0  |  | dev2 |   |
|  | dev1  |  +------+   |
|  +-------+             |
+------------------------+
```

可以结合内核中vfio.txt文件来理解Container、Group、Device和IOMMU之间的关系。

## VFIO Container

```c
// container: /dev/vfio/vfio
struct vfio_container {
	struct kref			kref;
	struct list_head		group_list;
	struct rw_semaphore		group_lock;
	struct vfio_iommu_driver	*iommu_driver;
	void				*iommu_data;
	bool				noiommu;
};
```

Container是管理内存资源，和IOMMU、DMA及地址空间相关，可以通过打开设备文件/dev/vfio/vfio来获取container对应的文件描述符，在内核vfio/vfio.c中有对应该vfio设备文件的具体操作实现，ioctl主要是可以获取IOMMU相关的信息，vfio会将用户态对IOMMU相关操作发给底层的vfio_iommu驱动进行操作，通过vfio ioctl提供的接口如下：

* 获取API versio
* 设置IOMMU的类型，如设置为常用的VFIO_TYPE1_IOMMU
* 获取IOMMU的信息
* 分配空间并进行DMA映射

``` c
int container, group, device, i;
struct vfio_iommu_type1_info iommu_info = { .argsz = sizeof(iommu_info) };
struct vfio_iommu_type1_dma_map dma_map = { .argsz = sizeof(dma_map) };

/* Create a new container */
container = open("/dev/vfio/vfio", O_RDWR);

if (ioctl(container, VFIO_GET_API_VERSION) != VFIO_API_VERSION)
    /* Unknown API version */

if (!ioctl(container, VFIO_CHECK_EXTENSION, VFIO_TYPE1_IOMMU))
    /* Doesn't support the IOMMU driver we want. */

/* Enable the IOMMU model we want */
ioctl(container, VFIO_SET_IOMMU, VFIO_TYPE1_IOMMU);

/* Get addition IOMMU info */
ioctl(container, VFIO_IOMMU_GET_INFO, &iommu_info);

/* Allocate some space and setup a DMA mapping */
dma_map.vaddr = mmap(0, 1024 * 1024, PROT_READ | PROT_WRITE,
                MAP_PRIVATE | MAP_ANONYMOUS, 0, 0);
dma_map.size = 1024 * 1024;
dma_map.iova = 0; /* 1MB starting at 0x0 from device view */
dma_map.flags = VFIO_DMA_MAP_FLAG_READ | VFIO_DMA_MAP_FLAG_WRITE;

ioctl(container, VFIO_IOMMU_MAP_DMA, &dma_map);
```

## VFIO Group

```c
// group: /dev/vfio/%group_id
struct vfio_group {
	struct kref			kref;
	int				minor;
	atomic_t			container_users;
	struct iommu_group		*iommu_group;
	struct vfio_container		*container;
	struct list_head		device_list;
	struct mutex			device_lock;
	struct device			*dev;
	struct notifier_block		nb;
	struct list_head		vfio_next;
	struct list_head		container_next;
	struct list_head		unbound_list;
	struct mutex			unbound_lock;
	atomic_t			opened;
	wait_queue_head_t		container_q;
	bool				noiommu;
	struct kvm			*kvm;
	struct blocking_notifier_head	notifier;
};
```

Group是IOMMU进行DMA隔离的最小硬件单元，设备属于哪个group取决于IOMMU和设备的物理结构，在设备直通时需要将一个group里的所有设备都分配给一个虚拟机，其实就是多个group可以从属于一个container，而group下的所有设备也随着该group从属于该container。这样能够做到DMA隔离，避免一个container里的device通过DMA来攻击获取另一个container里的数据。

对于一个PCI设备0000:06:0d.0::，通过readlink可以在sys文件目录下获取其iommu_group，比如该PCI设备在ID为26的IOMMU group中。

```
$ readlink /sys/bus/pci/devices/0000:06:0d.0/iommu_group
../../../../kernel/iommu_groups/26
```

设备挂载在pci bus下，可以使用 vfio-pci 来管理这个group。使用vfio-pci来管理设备时，首先从原来的驱动里unbind该PCI设备，然后将id写入新的vfio-pci路径下，会为这个group创建一个字符设备。

```
$ lspci -n -s 0000:06:0d.0
06:0d.0 0401: 1102:0002 (rev 08)
$ echo 0000:06:0d.0 > /sys/bus/pci/devices/0000:06:0d.0/driver/unbind
$ echo 1102 0002 > /sys/bus/pci/drivers/vfio-pci/new_id
```

当设备绑定到vfio之后，在/dev/vfio/路径下面会产生一个新的group id，通过该id可以获取到group，完成以下操作：

* 查询group状态，是否所有设备都绑定到vfio驱动
* 设置group的container
* 根据设备的BDF号为设备分配一个文件描述符

``` c
struct vfio_group_status group_status =
                { .argsz = sizeof(group_status) };
/* Open the group */
group = open("/dev/vfio/26", O_RDWR);

/* Test the group is viable and available */
ioctl(group, VFIO_GROUP_GET_STATUS, &group_status);

if (!(group_status.flags & VFIO_GROUP_FLAGS_VIABLE))
    /* Group is not viable (ie, not all devices bound for vfio) */

/* Add the group to the container */
ioctl(group, VFIO_GROUP_SET_CONTAINER, &container);

/* Get a file descriptor for the device */
device = ioctl(group, VFIO_GROUP_GET_DEVICE_FD, "0000:06:0d.0");
```

## VFIO Device

```c
struct vfio_device {
	struct kref			kref;
	struct device			*dev;
	const struct vfio_device_ops	*ops;
	struct vfio_group		*group;
	struct list_head		group_next;
	void				*device_data;
};
```

为了兼顾platform和pci设备，vfio统一对外提供 `struct vfio_device` 来描述vfio设备，并用device_data来指向如 `struct vfio_pci_device`。Device即设备，但与真正的物理设备有区别的是，对于一个在硬件上独立的设备，单独构成一个iommu group，而如果是multi-function的设备，多个function之间是互联的，相互可以访问对方的数据，所以必须放到一个group里面。

通过group的ioctl操作和设备的的BDF号获取到设备描述符之后，在vfio_pci中有对应描述符的内核操作vfio_pci_ops，这个ops是在vfio_pci设备驱动vfio_pci_probe调用的时候注册到PCI设备的，probe的时候还会将设备加入到对应的group中。vfio_pci设备的ops中比较重要的是 vfio_pci_ioctl函数，提供了如下功能：

* VFIO_DEVICE_GET_INFO：获取设备信息，region数量、irq数量等
* VFIO_DEVICE_GET_REGION_INFO：获取vfio_region的信息，包括配置空间的region和bar空间的region等
* VFIO_DEVICE_GET_IRQ_INFO：获取设备中断相关的信息
* VFIO_DEVICE_SET_IRQS：完成中断相关的设置
* VFIO_DEVICE_RESET：设备复位
* VFIO_DEVICE_GET_PCI_HOT_RESET_INFO：获取PCI设备hot reset信息
* VFIO_DEVICE_PCI_HOT_RESET：设置PCI设备 hot reset
* VFIO_DEVICE_IOEVENTFD：设置ioeventfd

要暴露设备的能力到用户态空间，要让用户态能够直接访问设备配置空间并处理设备中断，对于PCI设备而言，其配置其配置空间是一个VFIO region，对应着一块MMIO内存，通过建立dma重映射让用户态能够直接访问设备配置空间，另外还需要建立中断重映射以让用户态驱动处理设备中断事件。

``` c
struct vfio_device_info device_info = { .argsz = sizeof(device_info) };

/* Get a file descriptor for the device */
device = ioctl(group, VFIO_GROUP_GET_DEVICE_FD, "0000:06:0d.0");

/* Test and setup the device */
ioctl(device, VFIO_DEVICE_GET_INFO, &device_info);

for (i = 0; i < device_info.num_regions; i++) {
    struct vfio_region_info reg = { .argsz = sizeof(reg) };

    reg.index = i;

    ioctl(device, VFIO_DEVICE_GET_REGION_INFO, &reg);

    /* Setup mappings... read/write offsets, mmaps

        * For PCI devices, config space is a region */
}

for (i = 0; i < device_info.num_irqs; i++) {
    struct vfio_irq_info irq = { .argsz = sizeof(irq) };

    irq.index = i;

    ioctl(device, VFIO_DEVICE_GET_IRQ_INFO, &irq);

    /* Setup IRQs... eventfds, VFIO_DEVICE_SET_IRQS */
}

/* Gratuitous device reset and go... */
ioctl(device, VFIO_DEVICE_RESET);
```

## Container,group和device绑定

1.VFIO_SET_IOMMU: Container 绑定 IOMMU:

首先,VFIO的Container和IOMMU之间的绑定,通过在用户态通过ioctl调用VFIO_SET_IOMMU完成,绑定意味着将container管理的所有group都attach到IOMMU中,最终会将每个group中的每个设备都attach到IOMMU中,这意味着为设备建立IO页表完成初始化

```c
ioctl(container, VFIO_SET_IOMMU, VFIO_TYPE1_IOMMU)
    vfio_ioctl_set_iommu
    	list_for_each_entry(group, &container->group_list, container_next) {
		ret = driver->ops->attach_group(data, group->iommu_group);
            __iommu_attach_group
            	ret = __iommu_group_for_each_dev(group, domain,
					 iommu_group_do_attach_device);
                        __iommu_attach_device
                            arm_smmu_attach_dev
                                建立设备的IO页表
```

2.VFIO_GROUP_SET_CONTAINER: 将Group设置到对应的Container:

VFIO提供接口由用户态指定Group绑定到哪个Container中,这个绑定操作会将group记录到container的链表中进行管理,并且如果已经设置好了vfio_iommu_driver,会进行group的attach操作,并进而完成该group中的设备的IO页表初始化

```c
VFIO_GROUP_SET_CONTAINER:
    vfio_group_set_container
        driver = container->iommu_driver;
        if (driver) {
            ret = driver->ops->attach_group(container->iommu_data,
                            group->iommu_group);
            if (ret)
                goto unlock_out;
        }

        group->container = container;
        container->noiommu = group->noiommu;
        list_add(&group->container_next, &container->group_list);
```

3.Device和Group之间的绑定关系源自设备和IOMMU的物理拓扑结构

## 小结

VFIO内核组件的实现与Linux内核的IOMMU、设备模型等紧密相连，通过抽象出VFIO的概念来完成对Linux内核组件的封装。本文主要通过VFIO的用户态接口的使用来介绍了VFIO的几个基本概念，包括VFIO Container、Group和Device。要让物理设备通过VFIO驱动暴露给用户态，需要完成以下步骤：

* 首先将设备与原有驱动进行解绑，并重新绑定到VFIO驱动，VFIO驱动会为设备指定对应的group，设备属于哪个IOMMU group与设备和IOMMU的物理拓扑结构有关。
* 完成上述绑定之后，用户态驱动就可以通过 `/dev/vfio/vfio`获取到VFIO 的container，设置vfio_iommu_driver的类型，通过container可以间接访问IOMMU完成dma映射。
* 然后可以通过 `/dev/vfio/%group_id` 获取到设备所属的group，通过ioctl将该group上的所有设备加入到container中。
* 然后通过group和设备BDF号可以获取到VFIO device的fd，并通过vfio提供的接口访问设备的配置空间和irq信息等，完成在用户态访问物理设备。

VFIO设备直通有几个关键问题需要关注,如何访问直通设备的IO地址空间，如何完成中断重映射和DMA重映射让用户态驱动访问物理设备能力.

## Reference

* https://www.kernel.org/doc/Documentation/vfio.txt
* https://kernelgo.org/vfio-introduction.html
