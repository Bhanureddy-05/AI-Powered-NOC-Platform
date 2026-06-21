# Runbook: Unauthorized Access & Security Alerts

## Symptom
Multiple failed SSH, TACACS+, or SNMP authorization attempts logged on a core router or firewall.

## Triage Steps
1. **Audit Logs**: Query the central syslog or local AAA buffers: `show logging | include auth` or `show logging | include fail`.
2. **Identify IP**: Extract the source IP address of the failed attempts.
3. **Verify Admin Activities**: Confirm whether a NOC engineer is attempting access with wrong credentials or if a script is misconfigured.

## Resolution Steps
- **Block Source IP**: If unauthorized, add a temporary ACL blocking the source IP on the edge router:
  `ip access-list extended EDGE-IN`
  `deny ip host <attacker_ip> any`
- **Reset Credentials**: If credential compromise is suspected, coordinate a password rotation for local users or update central TACACS+ policies.
- **Enable CoPP Control**: Verify SSH access is restricted to authorized management subnets using access classes on line vty configuration:
  `line vty 0 4`
  `access-class 10 in`
