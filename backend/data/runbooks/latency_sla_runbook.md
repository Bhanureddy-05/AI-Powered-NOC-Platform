# Runbook: Latency SLA Breach & Packet Loss

## Symptom
A device registers latency spikes above 150ms or packet loss exceeding 1.0% over a 5-minute window, violating SLA targets.

## Triage Steps
1. **Ping Diagnostic**: Execute an extended ICMP ping to the device's loopback interface.
2. **Traceroute**: Run `traceroute` from an adjacent node to locate the hop where latency surges or packets are dropped.
3. **Interface Statistics**: Inspect active interfaces with `show interfaces status`. Check for CRC errors, collisions, or input errors which indicate physical layer issues (e.g. bad fiber or cabling).

## Resolution Steps
- **Interface Reset**: If errors are rising on a port, shut down and re-enable the port (`shutdown` then `no shutdown`).
- **Reroute Traffic**: If a WAN link has high latency due to carrier transit, temporarily adjust routing metrics (e.g. OSPF cost, BGP local preference) to divert traffic to the secondary ISP path.
- **QoS Validation**: Ensure Quality of Service (QoS) queues are not overflowing. Run `show policy-map interface` to check for drops.
