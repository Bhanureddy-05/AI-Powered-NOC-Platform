"""
app/services/copilot.py
========================
Resilient LLM & Vector Store wrapper.
Handles RAG indexing, LangChain agent tooling, and fallback simulated NLP execution
when API credentials or local ChromaDB extensions are missing.
"""

import os
import re
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, AsyncGenerator, Optional
from sqlalchemy.future import select

from app.db.session import async_session
from app.models.device import Device
from app.models.metric import DeviceMetric
from app.models.alert import Alert
from app.models.ticket import Ticket
from app.models.audit_log import AuditLog

logger = logging.getLogger("copilot_service")

# Try to import ML components for fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Try to import LangChain/ChromaDB components
try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document as LCDocument
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

# -------------------------------------------------------------
# Document and Vector Store Fallbacks
# -------------------------------------------------------------

class SimpleDocument:
    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}

class ResilientVectorStore:
    """
    RAG vector store with ChromaDB and in-memory TF-IDF semantic search fallbacks.
    """
    def __init__(self):
        self.documents: List[SimpleDocument] = []
        self.vectorizer = None
        self.doc_vectors = None
        self.chroma_db = None
        self.use_fallback = True
        
        # Determine if we can use Google Generative AI
        api_key = os.getenv("GEMINI_API_KEY")
        if HAS_LANGCHAIN and api_key:
            try:
                # Ensure data/chroma_db directory exists
                os.makedirs("./data/chroma_db", exist_ok=True)
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=api_key
                )
                self.use_fallback = False
                logger.info("LangChain Embeddings configured successfully.")
            except Exception as e:
                logger.warning(f"Failed to load LangChain Embeddings: {e}. Falling back to TF-IDF.")
                self.use_fallback = True
        else:
            logger.info("Using in-memory TF-IDF Vector Store fallback (No GEMINI_API_KEY or LangChain missing).")
            self.use_fallback = True

    def initialize_store(self, runbook_dir: str = "./data/runbooks"):
        """Loads and indexes runbook markdown files."""
        os.makedirs(runbook_dir, exist_ok=True)
        raw_docs = []
        
        # Load runbook files
        if os.path.exists(runbook_dir):
            for filename in os.listdir(runbook_dir):
                if filename.endswith(".md"):
                    filepath = os.path.join(runbook_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            raw_docs.append(SimpleDocument(
                                page_content=content,
                                metadata={"source": filename}
                            ))
                    except Exception as e:
                        logger.error(f"Error reading runbook {filename}: {e}")

        if not raw_docs:
            # Seed default fallback documentation if directory is empty
            raw_docs.append(SimpleDocument(
                page_content="Runbook: High CPU Usage Mitigation\n\nSymptom: CPU above 85%.\nSteps:\n1. Run show processes cpu sorted.\n2. Disconnect rogue users.\n3. Rollback config via copy startup-config running-config.",
                metadata={"source": "cpu_spike_runbook.md"}
            ))
            raw_docs.append(SimpleDocument(
                page_content="Runbook: Latency SLA Breach & Packet Loss\n\nSymptom: Latency > 150ms, Packet Loss > 1%.\nSteps:\n1. Ping Loopback.\n2. Run traceroute.\n3. Reroute via metric costs.",
                metadata={"source": "latency_sla_runbook.md"}
            ))

        self.documents = raw_docs

        if not self.use_fallback:
            try:
                # Format to LangChain documents
                lc_docs = [LCDocument(page_content=d.page_content, metadata=d.metadata) for d in self.documents]
                # Split documents
                splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
                split_docs = splitter.split_documents(lc_docs)
                
                self.chroma_db = Chroma.from_documents(
                    split_docs,
                    self.embeddings,
                    persist_directory="./data/chroma_db"
                )
                logger.info(f"Successfully indexed {len(split_docs)} chunks in ChromaDB.")
                return
            except Exception as e:
                logger.warning(f"Failed to build Chroma DB: {e}. Switching to TF-IDF.")
                self.use_fallback = True

        # TF-IDF Fallback index building
        if HAS_SKLEARN and self.documents:
            try:
                self.vectorizer = TfidfVectorizer(stop_words='english')
                texts = [doc.page_content for doc in self.documents]
                self.doc_vectors = self.vectorizer.fit_transform(texts)
                logger.info(f"TF-IDF search index populated with {len(self.documents)} runbooks.")
            except Exception as e:
                logger.error(f"Failed to initialize TF-IDF: {e}")

    def similarity_search(self, query: str, k: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves matching documentation chunks with source metadata.
        """
        if not self.use_fallback and self.chroma_db:
            try:
                results = self.chroma_db.similarity_search(query, k=k)
                return [{"content": doc.page_content, "source": doc.metadata.get("source", "unknown")} for doc in results]
            except Exception as e:
                logger.warning(f"ChromaDB search failed: {e}. Falling back to TF-IDF.")

        # Fallback to TF-IDF overlap similarity
        if HAS_SKLEARN and self.vectorizer is not None and self.doc_vectors is not None:
            try:
                query_vec = self.vectorizer.transform([query])
                sims = cosine_similarity(query_vec, self.doc_vectors).flatten()
                top_indices = sims.argsort()[::-1][:k]
                
                results = []
                for idx in top_indices:
                    if sims[idx] > 0.05:  # Relevance threshold
                        doc = self.documents[idx]
                        results.append({
                            "content": doc.page_content,
                            "source": doc.metadata.get("source", "runbook_fallback"),
                            "score": float(sims[idx])
                        })
                return results
            except Exception as e:
                logger.error(f"Fallback search failed: {e}")

        # Basic substring fallback
        results = []
        words = query.lower().split()
        for doc in self.documents:
            match_count = sum(1 for w in words if w in doc.page_content.lower())
            if match_count > 0:
                results.append({
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "score": match_count
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]

# Global Vector Store Instance
vector_store = ResilientVectorStore()

# -------------------------------------------------------------
# Operations Toolset Executions
# -------------------------------------------------------------

async def execute_db_query(table: str, filter_val: str = None) -> str:
    """Queries SQL inventory tables safely."""
    async with async_session() as session:
        if table.lower() == "devices":
            stmt = select(Device)
            if filter_val:
                stmt = stmt.where(Device.device_name.ilike(f"%{filter_val}%") | Device.ip_address.ilike(f"%{filter_val}%"))
            result = await session.execute(stmt)
            records = result.scalars().all()
            if not records:
                return "No devices matched the query."
            return "\n".join([f"- Device: {r.device_name} | IP: {r.ip_address} | Type: {r.device_type} | Status: {r.status} | Location: {r.location}" for r in records])
            
        elif table.lower() == "alerts":
            stmt = select(Alert).order_by(Alert.timestamp.desc()).limit(10)
            if filter_val:
                stmt = select(Alert).where(Alert.severity.ilike(f"%{filter_val}%") | Alert.status.ilike(f"%{filter_val}%")).order_by(Alert.timestamp.desc()).limit(10)
            result = await session.execute(stmt)
            records = result.scalars().all()
            if not records:
                return "No alerts found."
            return "\n".join([f"- Alert ID: {r.id} | Device ID: {r.device_id} | Type: {r.alert_type} | Severity: {r.severity} | Status: {r.status} | Msg: {r.message} | Time: {r.timestamp}" for r in records])

        elif table.lower() == "tickets":
            stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(10)
            if filter_val:
                stmt = select(Ticket).where(Ticket.priority.ilike(f"%{filter_val}%") | Ticket.status.ilike(f"%{filter_val}%")).order_by(Ticket.created_at.desc()).limit(10)
            result = await session.execute(stmt)
            records = result.scalars().all()
            if not records:
                return "No tickets found."
            return "\n".join([f"- Ticket ID: {r.id} | Device ID: {r.device_id} | Title: {r.title} | Severity: {r.severity} | Status: {r.status} | Created: {r.created_at}" for r in records])
            
        return f"Unknown database query target table: {table}"

async def execute_log_search(device_name: str, keyword: str = None) -> str:
    """Generates and searches simulated syslogs for a specific device."""
    now = datetime.utcnow()
    # Mock Syslogs base
    logs = [
        f"[{ (now - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S') }] %OSPF-5-ADJCHG: Neighbor 192.168.10.1 on GigabitEthernet0/1 changed state from FULL to DOWN: Interface Down",
        f"[{ (now - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S') }] %SEC-3-AAA_FAIL: SSH Authentication failed for administrator from 192.168.100.45",
        f"[{ (now - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S') }] %SYS-5-CONFIG_I: Configured from console by tech_ops",
        f"[{ (now - timedelta(minutes=45)).strftime('%Y-%m-%d %H:%M:%S') }] %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to down",
        f"[{ (now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S') }] %SYS-2-MEM_LOW: System memory usage exceeds 90% alert threshold",
    ]
    matched = []
    for log in logs:
        if keyword:
            if keyword.lower() in log.lower():
                matched.append(log)
        else:
            matched.append(log)
            
    if not matched:
        return f"No syslogs matching '{keyword}' found for device '{device_name}'."
    return f"Simulated Syslog for {device_name}:\n" + "\n".join(matched)

async def execute_metrics_retrieval(device_name: str) -> str:
    """Retrieves current performance metrics for the selected device."""
    async with async_session() as session:
        # Find device first
        dev_res = await session.execute(select(Device).where(Device.device_name.ilike(f"%{device_name}%")))
        device = dev_res.scalars().first()
        if not device:
            return f"Device '{device_name}' not found in database inventory."
            
        # Get latest metrics
        met_res = await session.execute(
            select(DeviceMetric)
            .where(DeviceMetric.device_id == device.id)
            .order_by(DeviceMetric.timestamp.desc())
            .limit(1)
        )
        metric = met_res.scalars().first()
        if not metric:
            return f"No telemetry metrics indexed for device '{device.device_name}' (ID: {device.id})."
            
        return (
            f"Latest Telemetry for {device.device_name} (IP: {device.ip_address}):\n"
            f"- CPU Usage: {metric.cpu_usage}%\n"
            f"- Memory Usage: {metric.memory_usage}%\n"
            f"- Bandwidth: {metric.bandwidth_usage} Mbps\n"
            f"- Latency: {metric.latency} ms\n"
            f"- Packet Loss: {metric.packet_loss}%\n"
            f"- Anomaly Score: {metric.anomaly_score}\n"
            f"- Diagnostic Time: {metric.timestamp}"
        )

async def execute_incident_remediation(ticket_id: int, status: str, notes: str) -> str:
    """Updates database ticket status or notes."""
    async with async_session() as session:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await session.execute(stmt)
        ticket = result.scalars().first()
        if not ticket:
            return f"Incident Ticket ID {ticket_id} not found."
            
        ticket.status = status
        # Simulate log entry
        log_entry = AuditLog(
            user_id=None,  # System/Agent actor
            action=f"Ticket {ticket_id} status updated to {status} by AI Agent.",
            details=f"Engineering Notes: {notes}",
            timestamp=datetime.utcnow()
        )
        session.add(log_entry)
        await session.commit()
        return f"Ticket ID {ticket_id} successfully updated to '{status}' with notes: '{notes}'."

# -------------------------------------------------------------
# Structured NOC Response Builder
# -------------------------------------------------------------

def _extract_metric(metrics_data: str, label: str) -> Optional[str]:
    """Extracts a named metric value from a formatted telemetry string."""
    if not metrics_data:
        return None
    for line in metrics_data.splitlines():
        if label.lower() in line.lower():
            parts = line.split(":")
            if len(parts) >= 2:
                return parts[1].strip()
    return None


def _determine_risk(metrics_data: Optional[str], q_lower: str, use_alerts: bool) -> str:
    """
    Determines risk level from live telemetry readings.
    Returns 'HIGH', 'MEDIUM', or 'LOW'.
    """
    if use_alerts:
        return "HIGH"

    if not metrics_data or "not found" in metrics_data.lower():
        return "UNKNOWN"

    cpu_str = _extract_metric(metrics_data, "CPU Usage")
    mem_str = _extract_metric(metrics_data, "Memory Usage")
    lat_str = _extract_metric(metrics_data, "Latency")
    pkt_str = _extract_metric(metrics_data, "Packet Loss")
    anom_str = _extract_metric(metrics_data, "Anomaly Score")

    def _fval(s: Optional[str]) -> float:
        try:
            return float(s.replace("%", "").replace("ms", "").replace("Mbps", "").strip()) if s else 0.0
        except (ValueError, AttributeError):
            return 0.0

    cpu = _fval(cpu_str)
    mem = _fval(mem_str)
    lat = _fval(lat_str)
    pkt = _fval(pkt_str)
    anom = _fval(anom_str)

    if cpu > 85 or mem > 90 or lat > 150 or pkt > 1.0 or anom > 0.7:
        return "HIGH"
    if cpu > 70 or mem > 75 or lat > 80 or pkt > 0.5 or anom > 0.4:
        return "MEDIUM"
    return "LOW"


def _risk_badge(risk: str) -> str:
    badges = {"HIGH": "🔴 **HIGH**", "MEDIUM": "🟡 **MEDIUM**", "LOW": "🟢 **LOW**", "UNKNOWN": "⚪ **UNKNOWN**"}
    return badges.get(risk, "⚪ **UNKNOWN**")


def _extract_runbook_steps(runbook_text: str) -> Dict[str, List[str]]:
    """
    Parses a runbook markdown document into triage steps and resolution steps.
    Returns {'triage': [...], 'resolution': [...]} lists of step strings.
    """
    triage: List[str] = []
    resolution: List[str] = []
    current_section = None

    for line in runbook_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        low = stripped.lower()
        if "triage" in low or "steps" in low:
            current_section = "triage"
        elif "resolution" in low or "mitigation" in low or "fix" in low:
            current_section = "resolution"
        elif stripped.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.")) and current_section:
            step = stripped.lstrip("-*0123456789. ").strip()
            if step and len(step) > 5:
                if current_section == "triage":
                    triage.append(step)
                else:
                    resolution.append(step)
    return {"triage": triage[:4], "resolution": resolution[:5]}


def _build_noc_response(
    query: str,
    q_lower: str,
    device_name: Optional[str],
    metrics_data: Optional[str],
    alerts_data: str,
    rag_doc_content: str,
    citations: List[str],
    use_metrics: bool,
    use_alerts: bool,
) -> str:
    """
    Constructs a structured, data-grounded NOC engineering report.
    All sections are derived from live telemetry and retrieved runbook content.
    """
    risk = _determine_risk(metrics_data, q_lower, use_alerts)
    steps = _extract_runbook_steps(rag_doc_content)
    triage_steps = steps["triage"]
    resolution_steps = steps["resolution"]

    device_label = device_name.upper() if device_name else "the queried device"

    # ── Pull live readings ──────────────────────────────────────────────────
    cpu_val = _extract_metric(metrics_data, "CPU Usage") or "N/A"
    mem_val = _extract_metric(metrics_data, "Memory Usage") or "N/A"
    lat_val = _extract_metric(metrics_data, "Latency") or "N/A"
    pkt_val = _extract_metric(metrics_data, "Packet Loss") or "N/A"
    bw_val = _extract_metric(metrics_data, "Bandwidth") or "N/A"
    anom_val = _extract_metric(metrics_data, "Anomaly Score") or "N/A"

    out = []
    out.append("---")
    out.append(f"## 📋 NOC Operations Intelligence Report\n")
    out.append(f"**Query:** _{query}_\n")
    out.append(f"**Risk Level:** {_risk_badge(risk)}\n")

    # ── Live Telemetry Summary ──────────────────────────────────────────────
    if metrics_data and "not found" not in metrics_data.lower():
        out.append("---")
        out.append(f"### 📡 Live Telemetry — {device_label}\n")
        out.append(f"| Metric | Value | Threshold | Status |")
        out.append(f"|--------|-------|-----------|--------|")

        def row(name, val, warn, crit, unit=""):
            try:
                v = float(str(val).replace("%", "").replace("ms", "").replace("Mbps", "").strip())
                if v >= crit:
                    status = "🔴 CRITICAL"
                elif v >= warn:
                    status = "🟡 WARNING"
                else:
                    status = "🟢 NORMAL"
            except (ValueError, TypeError):
                status = "⚪ N/A"
            return f"| {name} | {val}{unit} | >{warn}{unit} warn / >{crit}{unit} crit | {status} |"

        out.append(row("CPU Usage", cpu_val.replace("%",""), 70, 85, "%"))
        out.append(row("Memory Usage", mem_val.replace("%",""), 75, 90, "%"))
        out.append(row("Latency", lat_val.replace(" ms","").replace("ms",""), 80, 150, " ms"))
        out.append(row("Packet Loss", pkt_val.replace("%",""), 0.5, 1.0, "%"))
        out.append(f"| Bandwidth | {bw_val} | — | ⚪ INFO |")
        out.append(f"| Anomaly Score | {anom_val} | >0.4 warn / >0.7 crit | {'🔴 CRITICAL' if float(str(anom_val).strip() or 0) > 0.7 else ('🟡 WARNING' if float(str(anom_val).strip() or 0) > 0.4 else '🟢 NORMAL')} |")
        out.append("")

    # ── Root Cause Analysis ────────────────────────────────────────────────
    out.append("---")
    out.append("### 🔍 Root Cause Analysis\n")
    if "cpu" in q_lower:
        out.append(
            f"Sustained CPU pressure on **{device_label}** (currently at **{cpu_val}**) is most commonly caused by:\n"
            f"- **Route instability** — excessive OSPF/BGP reconvergence events generating high control-plane load\n"
            f"- **SNMP over-polling** — external monitoring probes querying at sub-1-minute intervals\n"
            f"- **Unauthorized sessions** — rogue terminal sessions or scripted brute-force attempts consuming vty lines\n"
            f"- **Recent config push** — a misconfigured ACL, routing policy, or QoS map increasing process overhead\n"
        )
    elif "latency" in q_lower or "packet" in q_lower:
        out.append(
            f"Elevated latency (**{lat_val}**) and packet loss (**{pkt_val}**) on **{device_label}** typically indicate:\n"
            f"- **Physical layer degradation** — bad fiber, faulty SFP, or cable CRC errors on the uplink interface\n"
            f"- **WAN carrier congestion** — transit provider throttling or rerouting during maintenance\n"
            f"- **QoS queue saturation** — low-priority traffic filling output queues, starving real-time flows\n"
            f"- **Interface duplex mismatch** — auto-negotiation failure causing half-duplex collision storms\n"
        )
    elif "memory" in q_lower or "mem" in q_lower:
        out.append(
            f"Memory utilization at **{mem_val}** on **{device_label}** suggests:\n"
            f"- **BGP/OSPF table growth** — large routing table expansion after a peer advertisement change\n"
            f"- **Leaked process memory** — a software bug in an IOS/NX-OS process not releasing allocated buffers\n"
            f"- **Large ACL or NAT table** — overloaded connection tracking exhausting the process heap\n"
        )
    elif use_alerts:
        out.append(
            f"Active critical alerts detected on the NOC board. Likely root causes:\n"
            f"- Interface or link failure causing downstream SLA breaches\n"
            f"- Threshold breach from a recent traffic surge or configuration change\n"
            f"- Automated anomaly detection flagged metric deviation from historical baseline\n"
        )
    else:
        out.append(
            f"Based on the retrieved telemetry and runbook context, no single dominant failure mode is identified. "
            f"Current metrics on **{device_label}** appear within acceptable bounds. Recommend proactive monitoring.\n"
        )

    # ── Immediate Actions ──────────────────────────────────────────────────
    out.append("---")
    out.append("### ⚡ Immediate Actions\n")
    if resolution_steps:
        for i, step in enumerate(resolution_steps, 1):
            out.append(f"{i}. {step}")
    else:
        # Inline fallback grounded to query intent
        if "cpu" in q_lower:
            out.append("1. SSH to device and run `show processes cpu sorted` — identify the top CPU consumer.")
            out.append("2. Check for route flapping: `show ip route summary` and `show ip ospf neighbor`.")
            out.append("3. Inspect SNMP polling frequency; increase interval to ≥5 minutes if sub-1-minute.")
            out.append("4. Apply Control Plane Policing (CoPP) to rate-limit non-critical management traffic.")
            out.append("5. If a recent config push is suspected, roll back: `copy startup-config running-config`.")
        elif "latency" in q_lower or "packet" in q_lower:
            out.append("1. Execute extended ICMP ping to device loopback to confirm reachability.")
            out.append("2. Run `traceroute` from adjacent node — identify the hop where latency diverges.")
            out.append("3. Check interface counters: `show interfaces status` for CRC errors or input drops.")
            out.append("4. Adjust OSPF cost or BGP local-preference to reroute traffic to secondary ISP path.")
            out.append("5. Validate QoS queues: `show policy-map interface` — look for tail-drop counters.")
        else:
            out.append("1. Review the NOC alert board for any correlated events on adjacent devices.")
            out.append("2. Pull device logs for the past 1 hour: `show logging last 100`.")
            out.append("3. Confirm SLA thresholds are correctly configured in the monitoring platform.")
    out.append("")

    # ── Verification Commands ──────────────────────────────────────────────
    out.append("---")
    out.append("### 🖥️ Verification Commands\n")
    if triage_steps:
        out.append("Run the following to confirm root cause and validate remediation:\n")
        out.append("```")
        for step in triage_steps:
            # Extract inline code snippets if present
            codes = re.findall(r"`([^`]+)`", step)
            if codes:
                for cmd in codes:
                    out.append(cmd)
            else:
                out.append(f"# {step}")
        out.append("```")
    else:
        out.append("```")
        if "cpu" in q_lower:
            out.append("show processes cpu sorted")
            out.append("show ip route summary")
            out.append("show snmp")
            out.append("show users")
        elif "latency" in q_lower or "packet" in q_lower:
            out.append("ping loopback repeat 100 timeout 2")
            out.append("traceroute <next-hop-ip> probe 5")
            out.append("show interfaces status")
            out.append("show policy-map interface")
        elif "memory" in q_lower:
            out.append("show processes memory sorted")
            out.append("show platform resources")
        else:
            out.append("show logging last 100")
            out.append("show interface summary")
        out.append("```")
    out.append("")

    # ── Recommended Follow-up ─────────────────────────────────────────────
    out.append("---")
    out.append("### 📌 Recommended Follow-up Actions\n")
    if "cpu" in q_lower:
        out.append("- **Open Incident Ticket** if CPU sustained above 85% for more than 10 minutes.")
        out.append("- **Schedule maintenance window** to upgrade IOS/NX-OS if bug-related memory leak is confirmed.")
        out.append("- **Review SNMP polling config** on all monitoring tools — enforce minimum 5-minute intervals.")
        out.append("- **Validate CoPP policy** is applied on all core routers to prevent control-plane saturation.")
    elif "latency" in q_lower or "packet" in q_lower:
        out.append("- **Escalate to carrier** if WAN link degradation is confirmed via traceroute hop analysis.")
        out.append("- **Engage field team** to inspect physical cabling and SFP transceiver if CRC errors persist.")
        out.append("- **Review QoS class-maps** — ensure real-time traffic (voice/video) is in EF/priority queue.")
        out.append("- **Update SLA dashboard** ticket with packet-loss readings for carrier SLA claim evidence.")
    elif "memory" in q_lower:
        out.append("- **Raise vendor TAC case** if memory leak is not resolving after process restart.")
        out.append("- **Plan IOS reload** during off-peak window if memory exhaustion is imminent (>95%).")
        out.append("- **Audit BGP peer advertisements** — check for prefix limit violations from upstream peers.")
    elif use_alerts:
        out.append("- **Acknowledge all active alerts** and assign to the on-call NOC engineer.")
        out.append("- **Correlate alert timestamps** with recent change management records.")
        out.append("- **Trigger automated runbook** for the highest-severity alert category.")
    else:
        out.append("- **Monitor metrics** over the next 30 minutes for any trend change.")
        out.append("- **Review audit logs** for any config changes made in the last 24 hours.")
        out.append("- **Validate monitoring thresholds** are aligned with current SLA contracts.")
    out.append("")

    # ── Active Alerts (if queried) ─────────────────────────────────────────
    if use_alerts and alerts_data and "No active" not in alerts_data:
        out.append("---")
        out.append("### 🚨 Active Critical Alerts\n")
        out.append("```")
        out.append(alerts_data[:600])
        out.append("```\n")

    # ── Referenced Runbooks ───────────────────────────────────────────────
    if citations:
        out.append("---")
        out.append("### 📚 Referenced Runbooks\n")
        for src in citations:
            out.append(f"- 📖 `{src}`")
        out.append("")

    out.append("---")
    out.append("_Report generated by AETHER NOC AI Copilot · All data sourced from live telemetry and runbook knowledge base._")

    return "\n".join(out)


# -------------------------------------------------------------
# Streaming Agent Wrapper
# -------------------------------------------------------------

class ResilientChatModel:
    """
    Orchestrates streaming AI agent replies using Gemini or fallback ReAct logic.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.real_llm_active = False
        
        if HAS_LANGCHAIN and self.api_key:
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=self.api_key,
                    temperature=0.2,
                    streaming=True
                )
                self.real_llm_active = True
                logger.info("Real LangChain ChatGoogleGenerativeAI loaded.")
            except Exception as e:
                logger.warning(f"Error loading ChatGoogleGenerativeAI: {e}. Falling back.")
                self.real_llm_active = False

    async def stream_response(self, query: str, session_history: List[Dict[str, str]] = None) -> AsyncGenerator[str, None]:
        """
        Streams response tokens, wrapping outputs with simulated agent thought processes.
        """
        if self.real_llm_active:
            # We stream actual agent execution or raw streaming completions
            try:
                # To keep it lightweight and extremely stable, we perform a structured RAG augmented generation prompt
                # and stream it. For full portfolio completeness, we also integrate tool references directly.
                prompt = self._compile_agent_prompt(query, session_history)
                async for chunk in self.llm.astream(prompt):
                    yield chunk.content
                return
            except Exception as e:
                logger.warning(f"Real LLM stream failed: {e}. Yielding fallback response.")

        # Fallback simulated ReAct executor
        async for chunk in self._simulated_react_agent_stream(query):
            yield chunk

    def _compile_agent_prompt(self, query: str, history: List[Dict[str, str]] = None) -> str:
        # Retrieve context from RAG
        rag_results = vector_store.similarity_search(query, k=2)
        context = ""
        for i, res in enumerate(rag_results):
            context += f"\n[Source: {res['source']}]\n{res['content']}\n"

        history_str = ""
        if history:
            for msg in history[-5:]:
                history_str += f"{msg['role'].upper()}: {msg['content']}\n"

        prompt = (
            "You are the AETHER AI Network Operations Center (NOC) Copilot, an expert AI engineer.\n"
            "Analyze the user query using the retrieved knowledge base runbooks context. CITE your sources.\n"
            "If relevant, recommend commands, diagnostic procedures, or database values.\n\n"
            f"Knowledge Base Runbook Context:\n{context}\n\n"
            f"Conversation History:\n{history_str}\n"
            f"User Query: {query}\n"
            "AI Copilot Response:"
        )
        return prompt

    async def _simulated_react_agent_stream(self, query: str) -> AsyncGenerator[str, None]:
        """
        Streams a high-fidelity simulated agent trace that executes the real python backend functions.
        This provides a premium interactive feel matching the dark mode glassmorphic UI.
        """
        yield "🤖 **AI Agent Reasoning Trace Initiated...**\n\n"
        await asyncio.sleep(0.4)
        
        # Decide which tools are needed
        q_lower = query.lower()
        use_metrics = any(w in q_lower for w in ["metric", "cpu", "memory", "bandwidth", "latency", "packet", "status", "health"])
        use_alerts = any(w in q_lower for w in ["alert", "critical", "warning", "severity", "open"])
        use_tickets = any(w in q_lower for w in ["ticket", "incident", "assign", "remediate"])
        use_runbooks = any(w in q_lower for w in ["runbook", "mitigate", "solve", "how to", "sla", "procedure"])
        
        device_match = re.search(r"(router|switch|firewall|server|verify-router-\d+|verify-\S+|core-\S+|edge-\S+)", q_lower)
        device_name = device_match.group(1) if device_match else None

        # --- Thought Step 1 ---
        yield "> **Thought:** Analyzing query intent. I will gather live telemetry, active alerts, and retrieve matching runbook procedures.\n"
        await asyncio.sleep(0.3)
        
        citations = []
        alerts_data = "No active alerts retrieved."
        metrics_data = None
        rag_doc_content = ""

        # Query Database (alerts)
        if use_alerts or use_tickets or (not use_metrics and not use_runbooks):
            yield f"> **Action:** database_query(table='alerts', filter='critical')\n"
            await asyncio.sleep(0.5)
            alerts_data = await execute_db_query("alerts", "critical")
            yield f"> **Observation:** Retrieved active network alerts:\n```\n{alerts_data[:300]}...\n```\n"
            await asyncio.sleep(0.3)

        # Query Metrics
        if use_metrics or device_name:
            target_device = device_name or "verify-router"
            yield f"> **Action:** metrics_retrieval(device_name='{target_device}')\n"
            await asyncio.sleep(0.5)
            metrics_data = await execute_metrics_retrieval(target_device)
            yield f"> **Observation:** Network telemetry status retrieved:\n```\n{metrics_data}\n```\n"
            await asyncio.sleep(0.3)

        # Query RAG — always run to retrieve the most relevant runbook
        search_term = (
            "latency" if "latency" in q_lower else
            "cpu" if "cpu" in q_lower else
            "memory" if "memory" in q_lower else
            "auth" if any(w in q_lower for w in ["auth", "ssh", "login", "access"]) else
            "packet" if "packet" in q_lower else
            query
        )
        yield f"> **Action:** RAG_retrieval(query='{search_term}')\n"
        await asyncio.sleep(0.6)
        try:
            rag_docs = vector_store.similarity_search(search_term, k=2)
            if rag_docs:
                for doc in rag_docs:
                    citations.append(doc["source"])
                    rag_doc_content += doc["content"] + "\n"
                yield f"> **Observation:** Retrieved runbook [{rag_docs[0]['source']}]:\n```markdown\n{rag_docs[0]['content'][:200]}...\n```\n"
            else:
                yield "> **Observation:** No direct matching runbook found. Proceeding with live telemetry data only.\n"
        except Exception as rag_exc:
            logger.error(f"RAG retrieval error: {rag_exc}")
            yield f"> **Observation:** RAG retrieval error: {rag_exc}. Proceeding with telemetry data.\n"
        await asyncio.sleep(0.3)

        # --- Thought Step 2 ---
        yield "> **Thought:** All data gathered. Synthesizing structured NOC engineering report from live telemetry and runbook procedures...\n\n"
        await asyncio.sleep(0.5)

        # Build structured, data-grounded NOC response
        response_text = _build_noc_response(
            query=query,
            q_lower=q_lower,
            device_name=device_name,
            metrics_data=metrics_data,
            alerts_data=alerts_data,
            rag_doc_content=rag_doc_content,
            citations=citations,
            use_metrics=use_metrics,
            use_alerts=use_alerts,
        )

        # Stream the final answer in chunks to simulate typing
        chunk_size = 20
        for i in range(0, len(response_text), chunk_size):
            yield response_text[i:i+chunk_size]
            await asyncio.sleep(0.008)

# Global model instance
copilot_model = ResilientChatModel()
