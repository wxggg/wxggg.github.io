## IOMMU 介绍

在计算机体系结构中IOMMU（Input Output Memory Management Unit）是将设备直接内存访问（DMA）的IO总线和物理内存连接的内存管理单元，和传统的MMU一样，IOMMU将设备可见的虚拟地址（IOVA）映射到物理地址。不同的平台有不同的IOMMU，如Intel的IOMMU，PCIE图形卡使用的图形重映射表（GART），Arm平台的IOMMU是SMMU（System Memory Management），它们主要功能都是完成设备可见的IOVA到物理地址的映射。

CPU和外设访问物理内存：
```
    +---------------------+
    |      Main Memory    |
    +---------------------+
               |
              pa
               |
         -------------
         |           |
    +--------+   +--------+
    | IOMMU  |   |  MMU   |
    +--------+   +--------+
         |           |
       iova          va
         |           |
    +--------+   +--------+
    | Device |   |  CPU   |
    +--------+   +--------+
```

相对于设备DMA直接访问内存，使用IOMMU有很明显的优点：
* 可以在内存中分配比较大的非连续区域，IOMMU可以将连续的虚拟地址映射到零散的物理地址
* 即使设备不支持足够长的内存寻址来访问整个物理内存，也可以通过IOMMU来完成整个内存的寻址。比如x86计算机可以额通过物理地址扩展（PAE）功能寻址超过4GB的内存，但是普通的32位PCI设备则无法寻址超过4GB的内存，有IOMMU则可以让设备访问整个物理内存。
* 由于设备无法直接读取或写入映射的物理内存，可以保护内存免受恶意设备进行DMA攻击和尝试错误的内存传输。
* 在虚拟化场景中，Guest OS可以使用非专门位虚拟化设计的硬件，比如将高性能硬件如显卡直通给虚拟机，通过DMA直接访问内存。在虚拟化环境中，所有的内存地址都由虚拟化程序（如Qemu）进行重映射，Guest OS使用DMA直接访问内存时会发生故障，只有IOMMU完成了重映射之后，Guest OS才可以驱动设备正确进行DMA访存。
* 在有些体系结构中，IOMMU还以类似地址重映射的方式进行中断重映射。
* IOMMU还可以支持外围设备内存分页，使用PCI-SIG PCIe地址转换服务（ATS）PRI扩展的外围设备可以检测并通知内存管理服务。

相对于DMA直接访问物理内存，使用IOMMU的缺点主要体现在额外的性能和内存开销，地址翻译和缺页处理会增加额外的性能开销，并且IOMMU需要在内存中为IO页表分配空间，在有些情况下IOMMU和CPU共享页表可以避免这一内存开销，比如设备和CPU共享虚拟地址SVA。

## Arm SMMU 数据结构

SMMU（System Memory Management Unit）是Arm平台的IOMMU，
SMMU为设备提供用设备可见的IOVA地址来访问物理内存的能力，体系结构中可能存在多个设备使用IOVA经过IOMMU来访问物理内存，IOMMU需要能够区分不同的设备，从而为每个设备引入了一个Stream ID，指向对应的STE（Stream Table Entry），所有的STE在内存中以数组的形式存在，SMMU记录STE数组的首地址。在操作系统扫描设备的时候会为其分配独有的Stream ID简称sid，设备通过IOMMU进行访存的所有配置都写在对应sid的STE中。

Stream Table：
```
                  +-------+
strtab_base ----- | STE 0 |
                  | STE 1 |
StreamID[n:0] ->  | STE 2 |
                  | STE 3 |
                  +-------+
```

STE表项中保存了从IOVA到PA的地址翻译过程，为了适应虚拟化场景下的访存需求，SMMU设计了类似EPT页表的两级地址翻译过程。Stage 1 完成从虚拟地址VA到中间地址IPA的翻译过程，stage 2 完成从IPA到实际物理地址的翻译过程。

Stream Table Entry：
```
Stream Table Entry (STE)
+-----------------------+ 
| Config | S1ContextPtr | -> CD -> Stage 1 translation tables
+-----------------------+
|  VMID  | S2TTB        | -> Stage 2 translation tables
+-----------------------+
| Other attributes,     |
| configuration         |
+-----------------------+
```

对于非虚拟化场景，设备使用IOVA经过IOMMU进行DMA只需要经过Stage 1的地址转换，因为多个设备可能使用一个设备，所以每个设备的STE中还记录了CD（Context Descriptor）表的信息，由S1ContextPtr指向内存中CD表的基地址，CD表也是一个数组，使用SubstreamID来进行访存，简称ssid，也叫做pasid，pasid是与进程关联的id，用于区分不同进程的虚拟地址空间。在使用pasid找到对应的CD表项之后，也就找到了Stage 1地址翻译的IO页表，保存在TTB0和TTB1中。

Context Descriptor：
```
                  +-------+
S1ContextPtr ---- |  CD 0 |
                  |  CD 1 |
SubStreamID   ->  |  CD 2 |
                  |  CD 3 |
                  +-------+

Context Desctriptor (CD)
+-----------------------+ 
| Configuration | TTB0  | 
+-----------------------+
|      ASID     | TTB1  |
+-----------------------+
```

值得一提的是，在一般情况下，进程通过设备驱动让设备进行DMA时使用的IOVA由内核态驱动分配，当存在多个进程时，将该内核态的IOVA映射到进程的虚拟地址空间即可，也就是说不同进程在DMA时其实使用的是相同的IOVA地址空间，所以这时只需要第0项CD即可，一般只需要在CD0中保存IO页表的基地址。然而，当需要统一设备的IO地址空间和进程的虚拟地址空间，如共享虚拟地址访问（SVA）时，则会用到多个CD项分别绑定不同进程的虚拟地址空间。

设备经过SMMU进行地址翻译是一个很复杂的过程，首先会根据设备的sid（Stream ID）找到对应的STE项，STE项中的配置信息记录了是否需要Bypass Stage 1 的地址翻译，Bypass意味着直接使用PA（或IPA），如果没有Bypass会根据sid（Substream ID）找到对应CD项，CD项中记录了Stage 1地址翻译的页表，会将VA翻译成IPA，然后如果STE中还配置了Stage 2 的页表翻译，会根据Stage 2地址翻译的页表，将IPA翻译成最终的PA地址，如果没有配置Stage 2地址翻译，则之前获取到的IPA就是最终的PA地址。

SMMU地址翻译过程：
```
                         VA
                          |
                    -----------
                    |         |
+---------------------+       |
| Stage 1 translation |    Bypass
|        VA->IPA      |       |
+---------------------+       |
                    |         |
                    -----------
                          |
                         IPA
                          |
                    -----------
                    |         |
+---------------------+       |
| Stage 2 translation |    Bypass
|        IPA->VA      |       |
+---------------------+       |
                    |         |
                    -----------
                          |
                         PA
```

## Arm SMMU V3 初始化

所有IOMMU相关的驱动都在内核 drivers/iommu 目录下面，arm平台的最新的架构SMMU-v3的驱动为arm-smmu-v3.c，SMMU本身是一个平台设备，`struct arm_smmu_device`结构体在内存中管理SMMU设备的关键信息，内核对SMMU设备本身的初始化过程主要就是在填充这个结构体。

```c
/* An SMMUv3 instance */
struct arm_smmu_device {
	struct device			*dev;
	void __iomem			*base;
	u32				features;
	u32				options;

	struct arm_smmu_cmdq		cmdq;
	struct arm_smmu_evtq		evtq;
	struct arm_smmu_priq		priq;

	int				gerr_irq;
	int				combined_irq;
	u32				sync_nr;

	unsigned long			ias; /* IPA */
	unsigned long			oas; /* PA */
	unsigned long			pgsize_bitmap;

#define ARM_SMMU_MAX_ASIDS		(1 << 16)
	unsigned int			asid_bits;
	DECLARE_BITMAP(asid_map, ARM_SMMU_MAX_ASIDS);

#define ARM_SMMU_MAX_VMIDS		(1 << 16)
	unsigned int			vmid_bits;
	DECLARE_BITMAP(vmid_map, ARM_SMMU_MAX_VMIDS);

	unsigned int			ssid_bits;
	unsigned int			sid_bits;

	struct arm_smmu_strtab_cfg	strtab_cfg;

	/* IOMMU core code handle */
	struct iommu_device		iommu;
};
```

驱动加载的入口为 arm_smmu_device_probe 函数，其主要做了如下几件事情：

 1. 从dts的SMMU节点或ACPI的SMMU配置表中读取SMMU中断等属性
 2. 用struct resource 来从设备获取到其资源信息，并IO重映射
 3. probe SMMU的硬件特性
 4. 中断和事件队列初始化
 5. 建立STE表
 6. 设备reset
 7. 将SMMU注册到IOMMU

### 1. 读取dts的SMMU节点信息

函数 arm_smmu_device_dt_probe 读取节点信息主要是从 smmu->dev->of_node中读取对应的属性，并记录到 smmu->options 中，此外还会检查 DMA 是否支持 coherent， 是的话会设置COHERENCY特性。
```c
if (of_dma_is_coherent(dev->of_node))
      smmu->features |= ARM_SMMU_FEAT_COHERENCY;
```

### 2. 获取设备资源信息并IO重映射

获取到SMMU设备的资源信息保存在 `struct resource` 结构体中，记录IO基地址，并用 smmu->base 记录完成IO重映射之后的基地址。之后就可以通过 smmu->base 加偏移读写SMMU的硬件寄存器。

```c
/* Base address */
res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
ioaddr = res->start;
smmu->base = devm_ioremap_resource(dev, res);
```

### 3. probe SMMU硬件特性

函数 arm_smmu_device_hw_probe 通过读取 SMMU 的寄存器获取SMMU的硬件特性，

IDR0寄存器：
```
reg = readl_relaxed(smmu->base + ARM_SMMU_IDR0);
```
* 是否支持：两级STE表、两级CD表
* 是否支持：PRI、ATS、SEV、MSI、HYP、STALL、Stage 1、Stage 2
* 获取：ias长度、asid_bits、vmid_bits

IDR1寄存器：
```c
reg = readl_relaxed(smmu->base + ARM_SMMU_IDR1);
```
* 获取：evtq和priq的队列长度、ssid_bits、sid_bits、

IDR5寄存器：
```c
reg = readl_relaxed(smmu->base + ARM_SMMU_IDR5);
```
* 获取：evtq最多能stall的的数量
* 是否支持：VAX、oas长度、pgsize_bitmap

### 4. 中断和事件队列初始化

函数 arm_smmu_init_structures 会完成内存中的数据结构的初始化，包括三条队列evtq、priq、cmdq，cmdq用于SMMU驱动向硬件发送命令，比如刷新TLB、写CD内容等，event队列用于SMMU上挂载的platform设备向驱动发送异常消息，priq队列功能类似只不过用于挂载的PCI设备。event队列和pri队列分别有各自的中断号完成异常事件的通知，此外还有一个gerror的中断号用于上报不可恢复（unrecoverable）的严重错误，其直接中断处理不需要队列。

```c
irq = platform_get_irq_byname(pdev, "combined");
if (irq > 0)
      smmu->combined_irq = irq;
else {
      irq = platform_get_irq_byname(pdev, "eventq");
      if (irq > 0)
            smmu->evtq.q.irq = irq;

      irq = platform_get_irq_byname(pdev, "priq");
      if (irq > 0)
            smmu->priq.q.irq = irq;

      irq = platform_get_irq_byname(pdev, "gerror");
      if (irq > 0)
            smmu->gerr_irq = irq;
}

/* Initialise in-memory data structures */
ret = arm_smmu_init_structures(smmu);
```

在驱动进行SMMU设备reset的时候，arm_smmu_setup_unique_irqs 会注册相应的事件处理，eventq和priq会注册内核线程完成事件处理，而对于不可恢复错误gerror则直接注册函数完成中断处理。

### 5. 建立STE表

根据SMMU的配置不同，可以建立两级或者线性STE表，相对于线性STE表，两级STE表不需要一开始创建所有的STE项，只需要先分配第一级的目录项即可。对于STE线性表，根据sid_bits和STE项的大小，在内存中用dma分配一块连续的内存，在配置中记录其基地址，然后将所有的STE项配置成默认情况下的bypass模式。

```c
static int arm_smmu_init_strtab_linear(struct arm_smmu_device *smmu)
{
	void *strtab;
	u64 reg;
	u32 size;
	struct arm_smmu_strtab_cfg *cfg = &smmu->strtab_cfg;

	size = (1 << smmu->sid_bits) * (STRTAB_STE_DWORDS << 3);
	strtab = dmam_alloc_coherent(smmu->dev, size, &cfg->strtab_dma,
				     GFP_KERNEL | __GFP_ZERO);

	cfg->strtab = strtab;
	cfg->num_l1_ents = 1 << smmu->sid_bits;

	/* Configure strtab_base_cfg for a linear table covering all SIDs */
	reg  = FIELD_PREP(STRTAB_BASE_CFG_FMT, STRTAB_BASE_CFG_FMT_LINEAR);
	reg |= FIELD_PREP(STRTAB_BASE_CFG_LOG2SIZE, smmu->sid_bits);
	cfg->strtab_base_cfg = reg;

	arm_smmu_init_bypass_stes(strtab, cfg->num_l1_ents);
	return 0;
}
```
### 6. 设备 reset

函数 arm_smmu_device_reset 会进行设备的复位操作，通过前面获取到的设备寄存器，对控制寄存器CR1和CR2写入队列内存属性等信息，对STRTAB_BASE寄存器写入STE表的基地址和配置信息，将三条队列在内存中的基地址、队首和队尾信息分别写入对应的寄存器中，之后 reset 会调用arm_smmu_setup_irqs注册中断事件的处理操作。

### 7. 将SMMU注册到IOMMU
 
不同平台的IOMMU设备在Linux内核中抽象出了统一的IOMMU接口，SMMU的初始化会在sys目录下面注册一个smmu->iommu设备节点，并且将arm_smmu_ops注册给该设备以及系统PCI总线和平台设备总线。这样当使用IOMMU公共接口时，会调用smmu提供的功能，具体可以查看arm_smmu_ops中提供的各种IOMMU接口实现。

```c
iommu_device_sysfs_add(&smmu->iommu, dev, NULL,
			     "smmu3.%pa", &ioaddr);

iommu_device_set_ops(&smmu->iommu, &arm_smmu_ops);
iommu_device_set_fwnode(&smmu->iommu, dev->fwnode);

iommu_device_register(&smmu->iommu);

bus_set_iommu(&pci_bus_type, &arm_smmu_ops);
bus_set_iommu(&platform_bus_type, &arm_smmu_ops);
```

## IOMMU与DMA

IOMMU的主要功能之一就是避免设备在进行DMA访问内存的时候直接使用物理地址不安全，所以就产生了IOVA地址，在dma_alloc分配内存的时候，首先在IO地址空间分配一个IOVA地址，然后在IOMMU管理的页表中建立IOVA和dma_alloc分配的物理地址的映射关系，外设在进行dma的时候，只需要使用IOVA地址即可。

调用 dma alloc 系列函数分配内存最终会调到 iommu_dma_alloc 函数，其会分配iova和实际的物理内存，并用iommu_map建立iova到物理内存的映射关系，也就是找到设备对应的STE，并找到CD项（一般是第0项），然后找到内存中对应的页表，将iova到物理地址的映射写入页表中，arm SMMU 相关的页表操作在 io-pgtable.c中完成。

```c
iommu_dma_alloc
      pages = __iommu_dma_alloc_pages(count, alloc_sizes >> PAGE_SHIFT, gfp);
      iova = iommu_dma_alloc_iova(domain, size, dev->coherent_dma_mask, dev);

      iommu_map_sg(domain, iova, sgt.sgl, sgt.orig_nents, prot
```

可以有多种方式bypass掉IOMMU，首先Linux提供了iommu.passthrough的方式，可以配置dma默认不走iommu，通过软件的地址映射技术swiotlb来访存；其次，SMMU v3驱动中提供了参数可以bypass掉某个SMMU；第三十可以在ACPI或者DTS中不配置对应的SMMU节点，这样系统加载的时候就不会probe对应的SMMU了。

## 小结

IOMMU的主要功能就是为设备访问物理内存提供IOVA到PA的映射，使得设备不会直接使用物理地址来访存比较安全。Arm SMMUv3 作为IOMMU的一种具体实现，为其提供相应的接口。与IOMMU相关的包括设备进行DMA操作，VFIO直通将设备硬件能力安全的暴露给用户态等，本质上都是为了建立设备能够识别的IOVA到实际物理地址的映射关系。

## Reference：
* https://en.wikipedia.org/wiki/Input%E2%80%93output_memory_management_unit
* https://developer.arm.com/documentation/ihi0070/latest
* https://kernel.taobao.org/2020/06/ARM-SMMU-and-IOMMU/