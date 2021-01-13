搭建Linux内核开发环境

* Linux 内核编译
* Qemu + GDB 启动调试
* buildroot 构建根文件系统

## Linux内核编译

```
git clone https://github.com/torvalds/linux.git
```

```
make ARCH=x86_64 x86_64_defconfig
make ARCH=x86_64 menuconfig
```

使用编译选项增加debug信息
```
Kernel hacking
	Compile-time checks and compiler options  --->
		[*] Compile-time checks and compiler options  --->
		[ ]   Reduce debugging information
		[*]   Provide GDB scripts for kernel debugging
```

## Qemu启动Linux内核

```
qemu-system-x86_64 \
        -kernel arch/x86/boot/bzImage \
        -boot c -m 2048 \
        -append "root=/dev/zero rw console=ttyS0,115200 acpi=off nokaslr" \
        -nographic
```

目前没有配文件系统，启动内核会提示错误

## buildroot配置根文件系统

```
git clone https://github.com/buildroot/buildroot
```

```
make menuconfig

Target Options
	-> Target Architecture
		(X) x86_64

Filesystem images
	-> ext2/3/4 root filesystem
		(X) ext4
```

启动Linux内核和rootfs，登录buildroot login: 输入root即可

```
qemu-system-x86_64 \
        -kernel arch/x86/boot/bzImage \
        -boot c -m 2048 \
        -hda /path/to/buildroot/output/images/rootfs.ext4 \
        -append "root=/dev/sda rw console=ttyS0,115200 acpi=off nokaslr" \
        -nographic
```

## GDB调试Linux内核

用GDB调试内核时需要在Kernel hacking中开启对应打编译选项，然后qemu启动时增加 -s -S 选项

```
qemu-system-x86_64 \
        -kernel arch/x86/boot/bzImage \
        -boot c -m 2048 \
        -hda /path/to/buildroot/output/images/rootfs.ext4 \
        -append "root=/dev/sda rw console=ttyS0,115200 acpi=off nokaslr" \
        -nographic \
        -s -S
```

启动后再开启一个shell启动gdb

```
gdb ./vmlinux

(gdb) target remote localhost:1234
Remote debugging using localhost:1234
0x000000000000fff0 in exception_stacks ()
(gdb) break start_kernel
Breakpoint 1 at 0xffffffff82b3caa9: file init/main.c, line 850.
(gdb) continue
Continuing.

Breakpoint 1, start_kernel () at init/main.c:850
850     {
(gdb) list
845     {
846             rest_init();
847     }
848
849     asmlinkage __visible void __init __no_sanitize_address start_kernel(void)
850     {
851             char *command_line;
852             char *after_dashes;
853
854             set_task_stack_end_magic(&init_task);
(gdb) 

```


## Link

* [Prepare the environment for developing Linux kernel with qemu.](https://medium.com/@daeseok.youn/prepare-the-environment-for-developing-linux-kernel-with-qemu-c55e37ba8ade)
