As we have mentioned before, the sharix os kernel part has been divided to several segment, which combines just like a big and complex program. And then we will come with memory paging and virtual memory.

## memory management
To probe the real physical memory,we use a struct E820 to store the memory information and this can be stored in 16bit mode and with help of bios interruption.
```c
struct e820map
{
	int nr_map;
	struct
	{
		uint64_t addr;
		uint64_t size;
		uint32_t type;
	}map[E820MAX];
};
```
In asmhead.S of real mode, we use the following code to store a struct e820map to 0x8000.
```c
probe_memory:
    movl $0, 0x8000
    xorl %ebx, %ebx
    movw $0x8004, %di
start_probe:
    movl $0xE820, %eax
    movl $20, %ecx
    movl $SMAP, %edx
    int $0x15
    jnc cont
    movw $12345, 0x8000
    jmp finish_probe
cont:
    addw $20, %di
    incl 0x8000
    cmpl $0, %ebx
    jnz start_probe
finish_probe:
```
### layout of kernel memory
In entry.S when we use ljmp, we appoint the exact segment number of kernel_cs. `ljmp $KERNEL_CS, $relocated`. Also, we have to set the stack segment, with code segment and stack segment been set, we can continue and run.
```c
#set up ebp, esp
	movl $0x0, %ebp
	# kernel stack ------   bootstack --->  bootstacktop
	# kernel stack size KSTACKSIZE(8KB)
	movl $bootstacktop, %esp

.data
.align PGSIZE
	.globl bootstack
bootstack:
	.space KSTACKSIZE
	.global bootstacktop
bootstacktop:
```
### physical memory manager
In this part, we use oop methodology to do the physical memory manager part.
```c
struct pmm_manager
{
	const char *name;
	void (*init)(void);
	void (*init_memmap)(struct Page *base, size_t n);
	struct Page *(*alloc_pages)(size_t n);
	void (*free_pages)(struct Page *base, size_t n);
	void (*check)(void);
	void (*pageinfo)(void);
};
```
In sharix, we use __buddy algorithm__ to manage the memory(discussed later).
```c
void pmm_init(void)
{
	init_pmm_manager();
	page_init();
	... //check
	/** boot_pgdir **/
	struct Page *p = alloc_page();
	boot_pgdir = (uintptr_t*)page2va(p);
	memset(boot_pgdir, 0, PGSIZE);
	boot_cr3 = PADDR(boot_pgdir);
	/* pgdir */
	// recursively insert boot_pgdir in itself
	// to form a virtual page table at virtual address VPT
	boot_pgdir[PDX(VPT)] = PADDR(boot_pgdir) | PTE_P | PTE_W;

	boot_map_segment(boot_pgdir, KERNBASE, KMEMSIZE, 0, PTE_W);

	//temporary map:
    //virtual_addr 3G~3G+4M = linear_addr 0~4M = linear_addr 3G~3G+4M = phy_addr 0~4M
	boot_pgdir[0] = boot_pgdir[PDX(KERNBASE)];

	enable_paging();
	gdt_init();
	...//print
}
```

### buddy algorithm
Them main purpose of this part is alloc_pages() and free_pages()

there is a global array, it stores the head of link of several pages which has different numbers
```c
// from 2^0 to 2^10
static free_area_t free_area[MAX_ORDER+1];
#define free_list(x) (free_area[x].free_list)
#define nr_free(x) (free_area[x].nr_free)
```

### linear mapping
physical memory & virtual memory & linear memory

physical mechanism of paging.
```c
static void enable_paging(void)
{
	lcr3(boot_cr3);
	// turn on paging
    uint32_t cr0 = rcr0();
    cr0 |= CR0_PE | CR0_PG | CR0_AM | CR0_WP | CR0_NE | CR0_TS | CR0_EM | CR0_MP;
    cr0 &= ~(CR0_TS | CR0_EM);
    lcr0(cr0);
//    cprintf("cr0:%x =============\n", cr0);
}
```
we need to set the physical address of boot_pgdir to cr3 register.
```c
struct Page *p = alloc_page();
	boot_pgdir = (uintptr_t*)page2va(p);
	memset(boot_pgdir, 0, PGSIZE);
	boot_cr3 = PADDR(boot_pgdir);
```
* p: Page pointer
* boot_pgdir: virtual address
* boot_cr3: physical address

We can test the addressing of paging with a check:
```c
int page_insert(uintptr_t *pgdir, struct Page *page, uintptr_t la, uint32_t perm)
{
	uintptr_t *pte_p = get_pte(pgdir, la);
	if(*pte_p != 0) {
		if(pte2page(*pte_p) != page)
			page_remove_pte(pgdir, la, pte_p);
	}
	*pte_p = page2pa(page) | PTE_P | perm;
	tlb_invalidate(pgdir, la);
	return 0;
}
```
```c
	struct Page *p;
	p = alloc_page();
	page_insert(boot_pgdir, p, 0x100, PTE_W);
	page_insert(boot_pgdir, p, 0x100+PGSIZE, PTE_W);
	page_insert(boot_pgdir, p, 0x100+2*PGSIZE, PTE_W);

	const char *str = "hello world!";
	char *c = (char*)0x100;
	strcpy((void*)0x100, str);
	int ret = strcmp((void*)0x100, (void*)(0x100+PGSIZE));
	cprintf("ret:%d str:%s str2:%s\n", ret, str, (char*)(0x100+2*PGSIZE));
```
and the result shows that the address 0x100 and 0x100+PGSIZE points to the same block of memory. There is only one page that is p, the address 0x100+PGSIZE is just mapped to page p.

## memory paging
This part is about the address mapping between physical address and virtual address. We need to set the two level page table properly so as to visit the VA(virtual address) correctly. If not, the paging fault will cause the system to break.

### page table entry
In x86 structure, the pte structure is as follows:
* totally 32 bits
* 11-0bit: [OS] 0 0 D A PCD PWT U/S R/W P
* 32-12bit: address of the page (notice here is __PHYSICAL ADDRESS__)

There are some properties in certain bit of the pte.
```c
/* page table/directory entry flags */
#define PTE_P           0x001                   // Present
#define PTE_W           0x002                   // Writeable
#define PTE_U           0x004                   // User
#define PTE_PWT         0x008                   // Write-Through
//...etc
```
Some functions and operation for the pte:
```c
1. struct Page * get_page(uintptr_t *pgdir, uintptr_t la)
2. int page_insert(uintptr_t *pgdir, struct Page *page, uintptr_t la, uint32_t perm)
{
	uintptr_t *pte_p = get_pte(pgdir, la);
	if(*pte_p != 0) {
		if(pte2page(*pte_p) != page)
			page_remove_pte(pgdir, la, pte_p);
	}
  //remember that the PTE_P and some other property can only
  //be written into the physical addresss
	*pte_p = page2pa(page) | PTE_P | perm;
	tlb_invalidate(pgdir, la);
	return 0;
}
3. uintptr_t * get_pte(uintptr_t *pgdir, uintptr_t la)
{
	uintptr_t *pde_p = &pgdir[PDX(la)];
	if(!(*pde_p & PTE_P)) {
		struct Page *page = alloc_page();
		uintptr_t pa = page2pa(page);
		memset((void*)VADDR(pa), 0, PGSIZE);
		*pde_p = pa | PTE_U | PTE_W | PTE_P;
	}
	return &((uintptr_t*)VADDR(PDE_ADDR(*pde_p)))[PTX(la)];
}
```

### page table
We have already set the struct Page * in somewhere in memory, and there's a mapping between the pointer and the real physic memory frame. But things stored in the page table is just a 4B items, and this should be the most important to set.

__a.first we need a frame to store the page table items.__
```c
struct Page *p = alloc_page();
	boot_pgdir = (uintptr_t*)page2va(p);
	memset(boot_pgdir, 0, PGSIZE);
	boot_cr3 = PADDR(boot_pgdir);
```
* boot_pgdir (virtual address) [0xc7fdf000]
* boot_cr3 (physical address) [0x7fdf000]

The boot_cr3 will be stored to register CR3. Since the enable_paging has not been opened, if we visit the virtual address, there will be no errors. But if we visit the virtual address after the paging is enabled, there might be some paging fault.

Here are some functions to operate page table item:


__b.form a virtual page table at  virtual address VPT(boot_pgdir)__
```c
// virtual page table
#define VPT 		0xFAC00000
#define PDX(la) ((((uintptr_t)(la)) >> 22) & 0x3FF)
#define PADDR(kva) ({uintptr_t __m_kva = (uintptr_t)(kva); \
					__m_kva - KERNBASE;})
boot_pgdir[PDX(VPT)] = PADDR(boot_pgdir) | PTE_P | PTE_W;
```
The virtual address VPT is mapped to the physic address of boot_pgdir(just boot_cr3), this makes us use the VPT as the address to visit boot_pgdir instead.

__c. memory mapping__
```c
boot_map_segment(boot_pgdir, KERNBASE, KMEMSIZE, 0, PTE_W);
static void boot_map_segment(uintptr_t *pgdir, uintptr_t la, size_t size, uintptr_t pa, uint32_t perm)
{
	size_t n = ROUND_UP(size + PG_OFF(la), PGSIZE) /PGSIZE;
	la = ROUND_DOWN(la, PGSIZE);
	pa = ROUND_DOWN(pa, PGSIZE);
	for(; n>0; n--,la+=PGSIZE,pa+=PGSIZE)	{
		uintptr_t *pte_p = get_pte(pgdir, la);
    //notice that the pte stores physical address
		*pte_p = pa | PTE_P | perm;
	}
}
result:
la:c0000000 get_pte alloc
//only alloc once for a page directory
//{pte pte pte ...}[1k pte]
la:c0400000 get_pte alloc
la:c0800000 get_pte alloc
```

### after enable_paging
Because we enabled paging, and the pte has stored the relative PA of LA, we should change the way gdt work. GDT do not have to do the -KERNBASE work anymore.
```c
#define SEG(type, base, lim, dpl)                           \
    (struct segdesc) {                                      \
    ((lim) >> 12) & 0xffff, (base) & 0xffff,            \
    ((base) >> 16) & 0xff, type, 1, dpl, 1,             \
    (unsigned)(lim) >> 28, 0, 0, 1, 1,                  \
    (unsigned) (base) >> 24                             \
}

static struct segdesc gdt[] = {
	SEG_NULL,
    [SEG_KTEXT] = SEG(STA_X | STA_R, 0x0, 0xFFFFFFFF, DPL_KERNEL),
    [SEG_KDATA] = SEG(STA_W, 0x0, 0xFFFFFFFF, DPL_KERNEL),
    [SEG_UTEXT] = SEG(STA_X | STA_R, 0x0, 0xFFFFFFFF, DPL_USER),
    [SEG_UDATA] = SEG(STA_W, 0x0, 0xFFFFFFFF, DPL_USER),
    [SEG_TSS]   = SEG_NULL,
};

static struct pseudodesc gdt_pd = {
	sizeof(gdt) -1, (uintptr_t)gdt
};
```
Notice that the base address have all turned from -KERNBASE to 0x0, which means there's no need for the gdt to do this. And the __boot_map_segment__ has already done this.

### to solve problem vram 0xfd000000
I have been trying to visit the physical memory address vram(0xfd000000), but for the reason that this address doesn't exist in the page table. Finally i understand and know how to solve this problem.
Just like the boot_map_segment has done, i change the name of the function to __map_physical_memory__, and use this function to map my vram to the linear vram. And we can just set them to the same address.
```c
static void map_physical_memory(uintptr_t *pgdir, uintptr_t la, size_t size, uintptr_t pa, uint32_t perm)
{
	size_t n = ROUND_UP(size + PG_OFF(la), PGSIZE) /PGSIZE;
	la = ROUND_DOWN(la, PGSIZE);
	pa = ROUND_DOWN(pa, PGSIZE);
	for(; n>0; n--,la+=PGSIZE,pa+=PGSIZE)
	{
		uintptr_t *pte_p = get_pte(pgdir, la);
    // cprintf("ptep:%x *ptep:%x n:%x pa:%x la:%x\n", pte_p, *pte_p, pa, la);
		*pte_p = pa | PTE_P | perm;
	}
}
//map vram memory to vram memory
	int nBppixel = binfo->bitspixel>>3;
	map_physical_memory(boot_pgdir, (uint32_t)binfo->vram, binfo->scrnx*binfo->scrny*nBppixel, (uint32_t)binfo->vram, PTE_W);
```

## virtual memory area and pagefault
The virtual memory area makes process to have much more memory then the system has physically. This is a good mechanism to make good use of the limited memory resource. We can swap the memory of process out if the process does not run for a long time.

If the memory of a running process is needed, but it is swapped out to the disk, the address we visit will cause a page fault, so we need to swap the memory in.

### vma (virtual memory area)
Here's a linklist to organize the vmm_struct of the same page directory.The mm_struct stores the base linklist of vmm_struct and some other information.
```c
// virtual memory area
struct vma_struct {
  struct mm_struct *vm_mm;
  uintptr_t vm_start;           // start address of vma
  uintptr_t vm_end;             // end address
  uint32_t vm_flags;            // flags of vma
  list_entry_t list_link;       // list link between sorted vm
};
// control struct for a set of vma using the same PDT
struct mm_struct {
  list_entry_t mmap_list;       // list link of sorted vm
  struct vma_struct *mmap_cache;    // link cache
  uintptr_t *pgdir;                 // PDT
  int map_count;                // count of vma
};
//find_vma
//vma_create
//insert_vma_struct
//mm_create
//mm_destroy
```

### page fault
If we visit an address that doesn't exist, then there'll be an page fault causing the cpu to interrupt. For example, to visit 0xfb000000 last time. We map the linear vram area to the physical vram area so that we can visit the virtual vram as the same as before.

### fault classification

__a.__ page not present

The visited page is not present, which means the linear address and the physical address does not mapped, because the page table entry of the address is empty.
* ptep = get_pte(pgdir, addr)
* page = alloc_page();
* page_insert(pgdir, page, addr, perm)

__b.__ the page is not in memory
The page table entry is not null, but the `Present` bit is `0`.
* swap

__c.__ priority is no equal
