# Runbook: High CPU Usage Mitigation

## Symptom
A network device (Router, Switch, or Firewall) registers sustained CPU usage above the 85% threshold.

## Triage Steps
1. **Identify the Process**: Connect to the device console and run `show processes cpu sorted`.
2. **Check Control Plane Traffic**: Ensure no route flapping or loop is occurring. Check OSPF/BGP neighbor states with `show ip route summary`.
3. **Verify SNMP Pollers**: Misconfigured external monitoring tools polling too frequently can cause spikes. Check SNMP logs using `show snmp`.

## Resolution Steps
- **Rate-limit Control Plane**: Configure Control Plane Policing (CoPP) to limit non-essential management traffic.
- **Identify Rogue Users**: Check active terminal lines via `show users`. Disconnect unauthorized sessions.
- **Rollback Changes**: If a recent config push caused the issue, revert to the startup configuration using `copy startup-config running-config`.
- **Reboot (Last Resort)**: If CPU continues spiking and device is unresponsive, schedule a reload window.
