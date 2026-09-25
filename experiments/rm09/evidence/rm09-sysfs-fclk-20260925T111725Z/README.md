# RM09 exact sysfs FCLK probe

The guarded probe requested FCLK0 `187498123`Hz with all apps unloaded. The
sysfs write returned success, but immediate readback remained `99999999`Hz.
The rate gate rejected the readback, so the frozen RM07 app was not loaded and
no real-tensor or 135-call benchmark ran.

The exit trap restored the safe state. The restore log reports
`starter_kit_restore=PASS`, FPGA manager `operating`, and FCLK0 `99999999`Hz;
the frozen RM07 package hash checks passed. The final driver log reports
`watchdog_timer_left_armed=0`, and a read-only status check confirmed the
rollback timer is inactive, starter-kit is active, FPGA manager is operating,
and FCLK0 remains `99999999`Hz.

The restore helper logged an internal `remove from slot 0 returns: -1`
message while unloading an already-unloaded slot; its command returned 0 and
it then loaded the starter-kit successfully. This is recorded in the raw
restore log; the helper and overall driver both report restore PASS.

Run directory on the board:
`/home/ubuntu/kv260-vlm-p2-cpu/runs/rm09-sysfs-fclk-20260925T111725Z/`.
Complete `driver.log`, `restore.log`, and the pre-change clock diagnostics are
preserved beside this note. The clock study is frozen at 100MHz after this
single guarded attempt.
