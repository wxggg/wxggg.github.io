Sharix has the meaning of sharing, which means it is for everyone to learn and improve. The sharix os is mainly based on the `ucore os` of the tsinghua university, you can find it on github. So what i am doing is mainly about adding a graphical subsystem to it, and also makes some part of ucore as simple as possible.

I will keep updating sharix os, and if you are interested in sharix, welcome to update it together. For now, the main purpose is to realize a simple desktop and window, and to realize terminal and text editing, maybe also realize the windows message mechanism.

I have studied `30 days to make an os` and the ucore course of Tsinghua University, so here comes a thought to my mind.I was wondering how to make a graphical os at the base of ucore using the thought of `30 days to make an os`. To be honest, the graphic part is not the essential part of operating system, there are some more important things to do. But since the important part has been done by the former people, we don't have to recreate something new which may cost much time but have little effort.

So as a beginner, i take graphic part as an interest to get myself focused on the sharix project. Still, the basic and important part of operating system will be on the way.

I have this sharix project stored on github. You can search sharixos or sharix to find it.

  * https://github.com/sharixos/sharix.git
  * [sharix v0.01](https://github.com/sharixos/sharix/releases/tag/v0.01)
  * [sharix v0.02](https://github.com/sharixos/sharix/releases/tag/v0.02)

As we all know that operating system is actually a complex and basic program which is quite close to the hardware. So to build a simple os, we need to know about the cpu and some hardware mechanism. Otherwise it is very useful to learn the AT&T assembling language, this will be really helpful at the begin and even later part of sharix.

## boot a simple kernel

As we all know that bios has done much of the initial work for us, so that we can just access the information by the bios interrupt. The bios also offer us with an entry of program, the entry is the famous 0x07c00 address, we should put the boot section of our os code to this, so that the whole of our system can be booted .

### bootsect
In sharix, the start symbol below will be loaded to the 0x07c00, and it will clear the register: [%ax %ds %es %ss], and then jmp to main. This code stays in boot/bootasm.S, the file will be compiled and linked to a 512B size file, and be the boot section.
```c
start:
	xorw %ax, %ax
	movw %ax, %ds
	movw %ax, %es
	movw %ax, %ss
    movw $0x800, %di
    jmp main

main:
	call read_intbios #this function will load the left os code(2 section) to 0x07e00
	jmp 0x7e00

spin:
	jmp spin
```
### the next 2 section
As has mentioned above, the bootsect instructioin will load the left 2 section to 0x7e00, and then the PC should go to 0x07e00 to run the left instructioin.

The next 2 section code locates in intbios/asmhead.S, this file actually do much of the initial work in real mode.
```c
  .global asmstart
  asmstart:
    jmp main

  main:
    call set_video_mode #this function set the video mode
```

```c
# Switch from real to protected mode, using a bootstrap GDT
# and segment translation that makes virtual addresses
# identical to physical addresses, so that the
# effective memory map does not change during the switch.
		cli
		lgdt gdtdesc
		movl %cr0, %eax
		orl $CR0_PE_ON, %eax
		movl %eax, %cr0


# Jump to next instruction, but in 32-bit code segment.
# Switches processor into 32-bit mode.
		ljmp $PROT_MODE_CSEG, $protcseg
```

### to summarize
set video mode and store the information of video to a certain place

Enable A20, probe the memory and store the information of memory to a certain place

set the GDT(global description table) register gdtdesc
change the mode from .code16 to .code32, this makes it possible to use C language as the fundamental language to make sharix

```c
.code32                                             # Assemble for 32-bit mode
protcseg:
    # Set up the protected-mode data segment registers
    movw $PROT_MODE_DSEG, %ax                       # Our data segment selector
    movw %ax, %ds                                   # -> DS: Data Segment
    movw %ax, %es                                   # -> ES: Extra Segment
    movw %ax, %fs                                   # -> FS
    movw %ax, %gs                                   # -> GS
    movw %ax, %ss                                   # -> SS: Stack Segment

# Set up the stack pointer and call into C. The stack region is from 0--start(0x7c00)
	movl $0x0, %ebp
	movl $0x7c00, %esp

call bootmain
```
### why divide
I have attemped to do the work above just in the bootsect, and it didn't work because the bootsect is too small. You might not encounter this problem if you do not need the graphical mode.

When i once added the graphical set code to the bootsect, it becomes bigger then 512B, which is unacceptable for a boot section. So i let the bootsect do only the work to load the other section and jmp to them, this enlarge the size to execute the 16bit code by which can we use the bios interrupt.

### call kern_entry
We have compiled the kernel to an ELF format file and now just need to read and resolve the ELF file.
```c
    // call the entry point from the ELF header
    // note: does not return
    ((void (*)(void))(ELFHDR->e_entry & 0xFFFFFF))();
```

## the real mode and protected mode
In real mode of x86 architecture, we use cs:ip as the address to access memory, the cs and ip are 16bit register, so that we can access 20bit address, which means we can access 1MB memory. This is because we use cs*16+ip as the real memory address, and the memory has been designed using 20 address lines.

The name "real mode" means the cs:ip address is the actural physical address to access.

### protected mode
In protected mode, we can use 32bit register and also 32 lines of address to access memory, which means we can access up to 4GB memory. We can use segments and paging when we  are in protected mode.

The reason why it is called protected mode is that we can control the permission of segment by cs

### global descriptor table
The global descriptor table is an array that holds multiple segment descriptors, whose starting address is stored in the global descriptor table register GDTR. GDTR is 48 bits long, in which 32 bits are base addresses, and 16 bits are segment boundaries.

The global descriptor table register (Global, Descriptor, Register, GDTR): points to the global segment descriptor table GDT Table

The local descriptor table register (Local Descriptor Table Register): points to the local segment descriptor table LDT LDTR
Register Descriptor Table

(IDTR): points to a table containing the entry point of the interrupt handler subroutine (IDT). (Interrupt)

Task register (Task, Register, TR): this register points to the current task information store, which is needed for the processor to perform task switching.

## GDT
GDT is an important table of os, the address of the table is stored in a register called GDTR. The machine will mainly use this to know the exact address of a CS value. In sharix, we will change this table several times to fit different situations.

About real mode addressing, in 16-bit mode, the CS register stores the real address of instruction. So there is no need to set the GDTR register.

### set gdt
set GDT before entering protected mode

There are two methods of memory protection in x86 architecture, paging and segmentation. Before we enter protected mode, we have to set gdt by lgdt.
```c
.data
# Bootstrap GDT
.p2align 2                                          # force 4 byte alignment
gdt:
    SEG_NULLASM                                     # null seg
    SEG_ASM(STA_X|STA_R, 0x0, 0xffffffff)           # code seg for bootloader and kernel
    SEG_ASM(STA_W, 0x0, 0xffffffff)                 # data seg for bootloader and kernel

gdtdesc:
    .word 0x17                                      # sizeof(gdt) - 1
    .long gdt                                       # address gdt
```
And the SET_ASM defined like the following, each item has 64bit:

| lim>>12 (16) | base (16) | base>>16 (8) | (0x90)type (8)| (0xc0)(lim>>28) (8)| base>>24 (8) |
| :-----------:  |:---------:| :----------:  | :-----------:  | :----------------:  | :----------:  |
| 0            | 0         | 0            | 0             |    0               |  0           |
| 0xffff       | 0x0       | 0x0          | 0x9a          |    0xff            |  0x0         |
| 0xffff       | 0x0       | 0x0          | 0x92          |    0xff            |  0x0         |



```c
#define SEG_NULLASM                                             \
    .word 0, 0;                                                 \
    .byte 0, 0, 0, 0

#define SEG_ASM(type,base,lim)                                  \
    .word (((lim) >> 12) & 0xffff), ((base) & 0xffff);          \
    .byte (((base) >> 16) & 0xff), (0x90 | (type)),             \
        (0xC0 | (((lim) >> 28) & 0xf)), (((base) >> 24) & 0xff)
```
### set gdt again
set GDT after kern_entry in entry.S (optional)

If we have set the loaded address of kernel at 0xC0100000, then we have to reset the GDT. Otherwise, if not, we can just go to kern_init in init.c, and continue our system. Here is the main operation in entry.S:
```c
kern_entry:
	lgdt REALLOC(__gdtesc) #we must send the real physical address to registers
	movl $KERNEL_DS, %eax
	movw %ax, %ds
	movw %ax, %es
	movw %ax, %ss
	ljmp $KERNEL_CS, $relocated

relocated:
	#set up ebp, esp
	movl $0x0, %ebp
	# kernel stack ------   bootstack --->  bootstacktop
	# kernel stack size KSTACKSIZE(8KB)
	movl $bootstacktop, %esp
	call kern_init
```
and the REALLOC has been defined as `#define REALLOC(x)  (x - KERNBASE)`
The new gdt is as follows:
```c
.align 4
__gdt:
	SEG_NULLASM
	SEG_ASM(STA_X | STA_R, - KERNBASE, 0xFFFFFFFF)
	SEG_ASM(STA_W, - KERNBASE, 0xFFFFFFFF)
__gdtesc:
	.word 0x17  			# sizeof(gdt) - 1
	.long REALLOC(__gdt)	# address gdt
```
| lim>>12 (16) | base (16) | base>>16 (8) | (0x90)type (8)| (0xc0)(lim>>28) (8)| base>>24 (8) |
| -----------  |:---------:| ----------:  | -----------:  | ----------------:  | ----------:  |
| 0            | 0         | 0            | 0             |    0               |  0           |
| 0xffff       | 0x0       | 0x0          | 0x9a          |    0xff            |  - 0xc0      |
| 0xffff       | 0x0       | 0x0          | 0x92          |    0xff            |  - 0xc0      |
the entry.s has also set the stack
```c
.data
.align PGSIZE
	.globl bootstack
bootstack:
	.space KSTACKSIZE
	.global bootstacktop
bootstacktop:
```
### gdb
We have set the gdt, and there are some complex changes between the real physical address and the virtual address or linear address.
In sharix, we can use `make debug` and the with gdb tools to see the memory.
```c
(gdb) p kern_init
$8 = {int (void)} 0xc010002a <kern_init>
(gdb) p binfo
$10 = (struct BOOTINFO *) 0x0
(gdb) x/50u 0xc0100000
0xc0100000 <kern_entry>:	0	0	0	0
0xc0100010 <kern_entry+16>:	0	0	0	0
0xc0100020 <relocated+7>:	0	0	0	0
0xc0100030 <kern_init+6>:	0	0	0	0
0xc0100040 <kern_init+22>:	0	0	0	0
0xc0100050 <kern_init+38>:	0	0	0	0
0xc0100060 <kern_init+54>:	0	0	0	0
0xc0100070 <kern_init+70>:	0	0	0	0
0xc0100080 <kern_init+86>:	0	0	0	0
0xc0100090 <kern_init+102>:	0	0	0	0
0xc01000a0 <kern_init+118>:	0	0	0	0
0xc01000b0 <cputch+11>:	0	0	0	0
0xc01000c0 <cputch+27>:	0	0
```
To take the video info as an example, we have saved the binfo to 0x0 when we set the video mode in asmhead.S.
```c
save_video_mode_info: // save binfo to physical 0x0
    movw $0x118, 0x2 #vmode
    movw 0x12(%di), %ax
    movw %ax, 0x4  #scrnx
    movw 0x14(%di), %ax
    movw %ax, 0x6  #scrny
    movb 0x19(%di), %al
    movb %al, 0x8  #bitspixel
    movb 0x1b(%di), %al
    movb %al, 0x9 #mem_model
    movl 0x28(%di), %eax
    movl %eax, 0xc  #vram
```
The 0x0 address here is the physical address, if we want to visit it after we have set gdt in entry.S, we should use `(struct BOOTINFO *)(0x0+KERNBASE)`, and the KERNBASE has been set as 0xC0000000.For example:
```c
#define ADR_BOOTINFO (0x00000000 + KERNBASE)
struct BOOTINFO *binfo = (struct BOOTINFO *) ADR_BOOTINFO;
cprintf("scrnx:%d  scrny:%d\n", binfo->scrnx, binfo->scrny);
```
### set gdt once again
set gdt the last time in pmm_init after paging.
```c
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
```c
/* gdt_init - initialize the default GDT and TSS */
static void
gdt_init(void) {
    // set boot kernel stack and default SS0
    load_esp0((uintptr_t)bootstacktop);
    ts.ts_ss0 = KERNEL_DS;

    // initialize the TSS filed of the gdt
    gdt[SEG_TSS] = SEGTSS(STS_T32A, (uintptr_t)&ts, sizeof(ts), DPL_KERNEL);

    // reload all segment registers
    lgdt(&gdt_pd);

    // load the TSS
    ltr(GD_TSS);
}

static inline void
lgdt(struct pseudodesc *pd) {
    asm volatile ("lgdt (%0)" :: "r" (pd));
    asm volatile ("movw %%ax, %%gs" :: "a" (USER_DS));
    asm volatile ("movw %%ax, %%fs" :: "a" (USER_DS));
    asm volatile ("movw %%ax, %%es" :: "a" (KERNEL_DS));
    asm volatile ("movw %%ax, %%ds" :: "a" (KERNEL_DS));
    asm volatile ("movw %%ax, %%ss" :: "a" (KERNEL_DS));
    // reload cs
    asm volatile ("ljmp %0, $1f\n 1:\n" :: "i" (KERNEL_CS));
}

```
