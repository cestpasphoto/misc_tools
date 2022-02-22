# admin
### syslog_summary.py
Provides a summary of system logs on linux since yesterday by
   * focusing on warnings or errors only
   * factorizing repeated messages
   * hiding some messages

Sample output:

	[      kernel x9  ] Thu 21:03:31 VBoxNetAdp: Successfully started.
	[      kernel x1  ] Thu 21:03:40 CIFS: No dialect specified on mount. Default has changed to a more secure dialec
	[     systemd x2  ] Thu 21:03:29 Configuration file /etc/systemd/system/postfix.service.d/override.conf is marked
	[     systemd x6  ] Thu 21:03:37 Dependency failed for GNOME XSettings service.
	[systemd-modules-load x1  ] Thu 21:03:29 Failed to find module 'nvidia-current-uvm'
	[      smartd x1  ] Thu 21:03:31 In the system's table of devices NO devices found to scan
	[NetworkManager x1  ] Thu 21:03:31 <warn>  [1644523411.8225] ifupdown: interfaces file /etc/network/interfaces.d/*
	[    pipewire x2  ] Thu 21:03:36 Failed to receive portal pid: org.freedesktop.DBus.Error.NameHasNoOwner: Could n