LKM means linux kernel module.

These days i am doing something about adding a kernel module to linux, so this blog is mainly about kernel module. This is the programming guide that i referenced

https://www.tldp.org/LDP/lkmpg/2.6/html/lkmpg.html

A kernel module extends  the functionality of the kernel without the need to reboot the system.Take device driver as an example, it allows the kernel to access hardware connected to the system. Without kernel module we have to add the code into the kernel source code, and rebuild and reboot the kernel, obviously this is complicated.

You can see the module that has already been loaded into the kernel by command `lsmod`, it reads information from `/proc/modules`.


## Hello World

This is a test for kernel module, two functions are necessary: `init_module` and `cleanup_module`
```c
/*
 *  hello-1.c - The simplest kernel module.
 */
#include <linux/module.h>	/* Needed by all modules */
#include <linux/kernel.h>	/* Needed for KERN_INFO */

int init_module(void)
{
	printk(KERN_INFO "Hello world 1.\n");

	/*
	 * A non 0 return means init_module failed; module can't be loaded.
	 */
	return 0;
}

void cleanup_module(void)
{
	printk(KERN_INFO "Goodbye world 1.\n");
}
```

### compile
This is a simple Makefile for a basic kernel module
```perl
obj-m += hello-1.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
```
After `make`, the Makefile will generate several files, in which there's a hello-1.ko, we can use `modinfo hello-1.ko` to see the information.

### load and remove module
use `insmod ./hello-1.ko` to load the module, you might need sudo to get permission. After loaded, you can use `lsmod` or cat the file `/proc/modules` to know whether the module is loaded. Since there are many modules, you can use `| grep 'hello'` to filter the information.
```perl
$cat /proc/modules | grep 'hello'
hello_1 16384 0 - Live 0x0000000000000000 (POE)
```
use `rmmod hello-1` to remove the module

__hello-2.c__
The init and exit function can be renamed with macros in linux/init.h
```c
/*
 *  hello-2.c - Demonstrating the module_init() and module_exit() macros.
 *  This is preferred over using init_module() and cleanup_module().
 */
#include <linux/module.h>	/* Needed by all modules */
#include <linux/kernel.h>	/* Needed for KERN_INFO */
#include <linux/init.h>		/* Needed for the macros */

static int __init hello_2_init(void)
{
	printk(KERN_INFO "Hello, world 2\n");
	return 0;
}

static void __exit hello_2_exit(void)
{
	printk(KERN_INFO "Goodbye, world 2\n");
}

module_init(hello_2_init);
module_exit(hello_2_exit);
```
adding 2 modules is simple in Makefile
```perl
obj-m += hello-1.o
obj-m += hello-2.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
```

__A slightly more complete example__
There are license,author and parameter in this example, the license and author are initialized with macros `MODULE_LICENSE` and `MODULE_AUTHOR`. The parameter is initialized with 3 params, name,data type and permissions bits.

```c
/*
 *  hello-5.c - Demonstrates command line argument passing to a module.
 */
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/stat.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Peter Jay Salzman");

static short int myshort = 1;
static int myint = 420;
static long int mylong = 9999;
static char *mystring = "blah";
static int myintArray[2] = { -1, -1 };
static int arr_argc = 0;

/*
 * module_param(foo, int, 0000)
 * The first param is the parameters name
 * The second param is it's data type
 * The final argument is the permissions bits,
 * for exposing parameters in sysfs (if non-zero) at a later stage.
 */

module_param(myshort, short, S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP);
MODULE_PARM_DESC(myshort, "A short integer");
module_param(myint, int, S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH);
MODULE_PARM_DESC(myint, "An integer");
module_param(mylong, long, S_IRUSR);
MODULE_PARM_DESC(mylong, "A long integer");
module_param(mystring, charp, 0000);
MODULE_PARM_DESC(mystring, "A character string");

/*
 * module_param_array(name, type, num, perm);
 * The first param is the parameter's (in this case the array's) name
 * The second param is the data type of the elements of the array
 * The third argument is a pointer to the variable that will store the number
 * of elements of the array initialized by the user at module loading time
 * The fourth argument is the permission bits
 */
module_param_array(myintArray, int, &arr_argc, 0000);
MODULE_PARM_DESC(myintArray, "An array of integers");

static int __init hello_5_init(void)
{
	int i;
	printk(KERN_INFO "Hello, world 5\n=============\n");
	printk(KERN_INFO "myshort is a short integer: %hd\n", myshort);
	printk(KERN_INFO "myint is an integer: %d\n", myint);
	printk(KERN_INFO "mylong is a long integer: %ld\n", mylong);
	printk(KERN_INFO "mystring is a string: %s\n", mystring);
	for (i = 0; i < (sizeof myintArray / sizeof (int)); i++)
	{
		printk(KERN_INFO "myintArray[%d] = %d\n", i, myintArray[i]);
	}
	printk(KERN_INFO "got %d arguments for myintArray.\n", arr_argc);
	return 0;
}

static void __exit hello_5_exit(void)
{
	printk(KERN_INFO "Goodbye, world 5\n");
}

module_init(hello_5_init);
module_exit(hello_5_exit);
```
To load this module, you can set the parameter like `insmod hello-5.ko myint=128`, and the value inside will be set.

### printk
The console might not get the printk information, so you need a complete terminal by `ctrl alt f1` or to `f6`, and `ctrl alt f7` back to graphical mode. Beside, the printk macros need `KERN_ALERT` like
```c
printk(KERN_ALERT "hello world");
```
The printk can be replaced by using __current__ to get current task's tty structure.  You can look inside that tty structure to find a pointer to a string write function, used to write a string to the tty. In the example print_string.c, you can insmod the module in user terminal, and the information will be printed.

* print_string.c - Send output to the tty we're running on, regardless if it's through X11, telnet, etc.  We do this by printing the string to the tty associated with the current task.

### flashing keyboard LEDs
You can communicate the external world by kernel module programing, the keyboard leds is such an example. One of the keyboard led will keep blinking when the module is loaded.
* kbleds.c - Blink keyboard leds until the module is unloaded.

## Character Device File
Linux kernel modules is different from general programs, a program always begins from a main function, while modules are not. A kernel module start from the init_module function, and exit with the module_exit function.

There are two types of devices: character devices and block devices, the block devices have a buffer for requests. When the system was installed, device files are all created by the __mknod__ command, for example `mknod /dev/coffee c 12 2` command can create a new char device named 'coffee' with major/minor number 12 and 2. By convention you should put your device files into /dev

The major number of the file is used to determined which driver should be used to handle the access. The minor number is used to distinguish between different pieces of hardware.

The file_operations structure is defined in linux/fs.h, the instance can be described
```c
struct file_operations fops = {
	.read = device_read,
	.write = device_write,
	.open = device_open,
	.release = device_release
};
```
The struct file is different from __FILE__ defined in glibc, each device is represented in the kernel by a file structure. The struct file is a kernel level structure and never appears in a user space program.

### register a device
Char devices are accessed through device files, adding a driver to your system means registering it with the kernel.
```c
int register_chrdev(unsigned int major, const char *name, struct file_operations *fops);
```
The total example is [chardev.c](/static/file/program/linux/chardev.c), After compile and load the module, you need to do
```perl
$mknod /dev/DEVICE_NAME c Major 0
```
In that command, the DEVICE_NAME represents the name of the device, and the Major represents the return value of register_chrdev. This command can create a device node just for the module.

### visit device

To visit the device file with `cat /dev/chardev`, this is a read operation, and the order is device_open -> device_read -> device_read -> device_release.

And in device_open and device_release there are `try_module_get(THIS_MODULE)` and `module_put(THIS_MODULE)`.
* __try_module_get__: increment the use count
* __module_put__: decrement the use count

The key operation in read is __put_user__, this function copies data from the kernel data segment to the user data segment, so that the information in device can print on the user screen.
```c
put_user(*(msg_Ptr++), buffer++);
```

### Talking to Device Files
To talk to general device files, in unix you can use ioctl, every device has its own ioctl commands, including read and write ioctl.

The example contains several files:

* chardev.c - Create an input/output character device
* chardev.h - the header file with the ioctl definitions.
* ioctl.c - the process to use ioctl's to control the kernel module

## the proc File System
The /proc file system is a mechanism for the kernel and the kernel modules to send information to processes. For example, /proc/modules stores the information of all loaded modules, the /proc/devices stores the information of the loaded devices.

This is an example to create `/proc/helloworld`, it is necessary to notice that the function __create_proc_entry__ has been replaced by __proc_create__ since the linux kernel version 3.8.

[procfs1.c](/static/file/program/linux/procfs1.c)

There seems to be some problem in this program, because it should be like the following if you do the following, but it is right in new version example.
```perl
$cat /proc/helloworld
Hello World!
```

### new version
It is good to see that i have found the updated version of the linux kernel module examples on github. Thanks to the authors who update these examples.

https://github.com/bashrc/LKMPG

The reason why i got an error below is because the header `<asm/uaccess.h>` has been replaced with `<linux/uaccess.h>`.
```perl
error: implicit declaration of function ‘copy_from_user’
```

The function copy_from_user is necessary, kernel module and user program are distributed in different segments. So to communicate the copy_from_user and other similar functions like copy_to_user are needed.

Just like the printk, only __KERN_ALERT__ can print information, the __pr_alert__ is the new print function.

### seq_file
The seq_file is an API that helps formating a /proc file for output, which is based on sequence, composed of 3 functions: start(), next(), and stop(). When a user read the /proc file, the seq_file API starts a sequence.

Caution: when a sequence is finished, another starts. The start() will begin when the function stop() ends.

The example is procfs4.c.

more information:

https://lwn.net/Articles/22355/

## the System Calls

The location in the kernel where a process can jump to is called system_call. The process checks the system call number, and find in the sys_call_table to see the address of the kernel function to call.

The major on this blog is about change the kernel function to call by kernel module.

### library functions and system calls
It is obvious that system calls are all in kernel space and library functions are in user space, so they are essentially different. Take an example to see the syscalls of a program.
```c
#include <stdio.h>
int main(void)
{
    printf("hello");
    return 0;
}
```
Compile the code with __gcc -Wall -o hello hello.c__, and then run __strace ./helo__, then every line you see is a system call.
```c
execve("./hello", ["./hello"], [/* 91 vars */]) = 0
brk(NULL)                               = 0xf2d000
access("/etc/ld.so.nohwcap", F_OK)      = -1 ENOENT (No such file or directory)
access("/etc/ld.so.preload", R_OK)      = -1 ENOENT (No such file or directory)
open("/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
fstat(3, {st_mode=S_IFREG|0644, st_size=122136, ...}) = 0
mmap(NULL, 122136, PROT_READ, MAP_PRIVATE, 3, 0) = 0x7fcb4d770000
close(3)                                = 0
access("/etc/ld.so.nohwcap", F_OK)      = -1 ENOENT (No such file or directory)
open("/lib/x86_64-linux-gnu/libc.so.6", O_RDONLY|O_CLOEXEC) = 3
read(3, "\177ELF\2\1\1\3\0\0\0\0\0\0\0\0\3\0>\0\1\0\0\0P\t\2\0\0\0\0\0"..., 832) = 832
fstat(3, {st_mode=S_IFREG|0755, st_size=1868984, ...}) = 0
mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7fcb4d76f000
mmap(NULL, 3971488, PROT_READ|PROT_EXEC, MAP_PRIVATE|MAP_DENYWRITE, 3, 0) = 0x7fcb4d19f000
mprotect(0x7fcb4d35f000, 2097152, PROT_NONE) = 0
mmap(0x7fcb4d55f000, 24576, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_FIXED|MAP_DENYWRITE, 3,0x1c0000) = 0x7fcb4d55f000
mmap(0x7fcb4d565000, 14752, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_FIXED|MAP_ANONYMOUS, -1, 0) = 0x7fcb4d565000
close(3)                                = 0
mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7fcb4d76e000
mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7fcb4d76d000
arch_prctl(ARCH_SET_FS, 0x7fcb4d76e700) = 0
mprotect(0x7fcb4d55f000, 16384, PROT_READ) = 0
mprotect(0x600000, 4096, PROT_READ)     = 0
mprotect(0x7fcb4d78e000, 4096, PROT_READ) = 0
munmap(0x7fcb4d770000, 122136)          = 0
fstat(1, {st_mode=S_IFCHR|0620, st_rdev=makedev(136, 19), ...}) = 0
brk(NULL)                               = 0xf2d000
brk(0xf4e000)                           = 0xf4e000
write(1, "hello", 5hello)                    = 5
exit_group(0)                           = ?
+++ exited with 0 +++
```

### change system call kernel function
To change the kernel function, we need to implement our own one, and then change the pointer sys_call_table points to. It's important for cleanup_module to restore the table.

The example is syscall.c.

The key operation is in init_module and exit_module, in init_module as follows, the operation on cr0 is to get back to 16-bit mode. In 16-bit mode there is no page privilege, so we can rewrite the sys_call_table.
```c
static int __init syscall_start(void)
{
    if(!(sys_call_table = aquire_sys_call_table()))
        return -1;

    original_cr0 = read_cr0();

    write_cr0(original_cr0 & ~0x00010000);

    /* keep track of the original open function */
    original_call = (void*)sys_call_table[__NR_open];

    /* use our open function instead */
    sys_call_table[__NR_open] = (unsigned long *)our_sys_open;

    write_cr0(original_cr0);

    pr_alert("Spying on UID:%d\n", uid);

    return 0;
}
```
The exit_module is all about restoring everything back.

### Blocking Processes
Every time if a thread is bothered because some conditions are not satisfied, it will be blocked and put into a wait queue. If the condition is satisfied again, the threads on the queue will all be awoken.

Take the kernel module as an example, the file /proc/sleep can only be opened by a single process at a time. If the file is already opened, the kernel module calls __wait_event_interruptible__, which changes the status of the task to __TASK_INTERRUPTIBLE__, added to WaitQ.

When the file is closed by the process, module_close is called, which waikes up all the processes in the queue. One of the processes will get the control, and will start at the point right after the call to __module_interruptible_sleep_on__. The process can then set a global variable to tell all the other processes that the file is still open, and other processes will see it and go back to sleep.

The `tail -f ` can be used to keep the file open in the background, only if the background process is killed with `kill %1` can other processes have chance to access the file.

Sometimes processes don't want to sleep, and just want to get the resources or be told it cannot be done (kinds like the tryLock). The flag __O_NONBLOCK__ is used when processes open the file.

* sleep.c - create a /proc file, and if several processes try to open it at the same time, put all but one to sleep
* cat_noblock.c - open a file and display its contents, but exit rather than wait for input

```perl
$cat /proc/sleep
Last input:
$./cat_block /proc/sleep
Last input:
$tail -f /proc/sleep &
[1] 12148
Last input:
$./cat_block /proc/sleep
Open would block
$kill %1
[1]  + 12148 terminated  tail -f /proc/sleep
$./cat_noblock /proc/sleep
Last input:
```

## the Scheduling Tasks
Some tasks need to be done at certain time, if the task is to be done by a process, we can put it in the __crontab__ file.

If the task is to be done by a kernel module, we have two ways. We can put a process in the __crontab__ file, and then the process will wakeup the module by a system call when it is necessary. Obviously this is quite inefficient.

The other way is to create a function that will be called once for every timer interrupt. We can create a task and held it in a workqueue_struct structure, the structure will hold a pointer to the function. And then use queue_delayed_work to put that task on a task list called my_workqueue, which is the list of tasks to be executed on the next timer interrupt.

Everytime the function is called, we need to put it back on __my_workqueue__ so that the functiion will keep on being executed.

__example__
sched.c - schedule a function to be called on every timer interrupt.

### Interrupt Handlers
We all know that there should be a handler function for the interrupt. When the relevant IRQ is received, the function request_irq() is called, which receves the IRQ number, name of function, flags, a name for /proc/interrupts and a prameter to pass to the interrupt handler.

### Keyboards on the Intel Architecture
Write something for the keyboard interrupt, and disable the regular keyboard interrupt handler first.
* intrpt.c - An interrupt handler

and more for Symmetric Multi-Processing
