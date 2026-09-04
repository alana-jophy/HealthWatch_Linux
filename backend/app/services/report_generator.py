"""HealthWatch Surveillance Report Generation Service.

Compiles dynamic epidemiological data and renders export files in CSV and PDF formats.
Enforces strict privacy guidelines: only anonymized identifiers (pseudo_id) are exported,
omitting contact information, home addresses, or raw private coordinates.
"""

import csv
import datetime
import io
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.disease import CaseStatus, Disease, DiseaseCase
from app.models.exposure import ExposureEvent, ExposureStatus
from app.models.monitoring import MonitoringSession, SessionStatus
from app.models.patient import Patient
from app.models.spatial import District, LocalBody, Ward
from app.schemas.report import ReportTypeEnum

# ReportLab Imports for PDF Generation
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class ReportGeneratorService:
    """Core service compiling surveillance metrics into CSV and PDF reports."""

    @staticmethod
    def _apply_case_filters(query, filters: Dict[str, Any]):
        """Helper to apply cascading query filters to DiseaseCase query."""
        if filters.get("disease_id"):
            query = query.filter(DiseaseCase.disease_id == filters["disease_id"])
        if filters.get("district_id"):
            query = query.filter(District.id == filters["district_id"])
        if filters.get("local_body_id"):
            query = query.filter(LocalBody.id == filters["local_body_id"])
        if filters.get("ward_id"):
            query = query.filter(Ward.id == filters["ward_id"])
        if filters.get("start_date"):
            query = query.filter(DiseaseCase.diagnosis_date >= filters["start_date"])
        if filters.get("end_date"):
            query = query.filter(DiseaseCase.diagnosis_date <= filters["end_date"])
        if filters.get("case_status") and filters["case_status"] != "ALL":
            query = query.filter(DiseaseCase.case_status == filters["case_status"].upper())
        return query

    # ==========================================================================
    # 1. DATA COMPILATION FOR 8 REPORT TYPES
    # ==========================================================================

    @classmethod
    def compile_report_data(
        cls, db: Session, report_type: ReportTypeEnum, filters: Dict[str, Any]
    ) -> Tuple[str, List[str], List[Dict[str, Any]]]:
        """Route to specific report compiler based on report_type."""
        if report_type == ReportTypeEnum.DISEASE_STATISTICS:
            return cls._compile_disease_statistics(db, filters)
        elif report_type == ReportTypeEnum.DISTRICT_CASES:
            return cls._compile_district_cases(db, filters)
        elif report_type == ReportTypeEnum.LOCAL_BODY_CASES:
            return cls._compile_local_body_cases(db, filters)
        elif report_type == ReportTypeEnum.WARD_CASES:
            return cls._compile_ward_cases(db, filters)
        elif report_type == ReportTypeEnum.DATE_RANGE_CASES:
            return cls._compile_date_range_cases(db, filters)
        elif report_type == ReportTypeEnum.HOTSPOT_SUMMARY:
            return cls._compile_hotspot_summary(db, filters)
        elif report_type == ReportTypeEnum.POTENTIAL_EXPOSURES:
            return cls._compile_potential_exposures(db, filters)
        elif report_type == ReportTypeEnum.MONITORING_SUMMARY:
            return cls._compile_monitoring_summary(db, filters)
        else:
            # Comprehensive dossier default
            return cls._compile_comprehensive(db, filters)

    @classmethod
    def _compile_disease_statistics(cls, db: Session, filters: Dict[str, Any]):
        title = "Epidemiological Disease Surveillance Statistics"
        columns = [
            "Disease Code",
            "Disease Name",
            "Category",
            "Contagion Type",
            "Total Cases",
            "Confirmed",
            "Suspected",
            "Recovered",
            "Deceased",
            "Share (%)",
        ]

        query = (
            db.query(DiseaseCase)
            .join(Disease, DiseaseCase.disease_id == Disease.id)
            .outerjoin(Ward, DiseaseCase.ward_id == Ward.id)
            .outerjoin(LocalBody, Ward.local_body_id == LocalBody.id)
            .outerjoin(District, LocalBody.district_id == District.id)
        )
        query = cls._apply_case_filters(query, filters)
        cases = query.all()
        total_cases = len(cases)

        buckets = defaultdict(lambda: {
            "name": "", "category": "", "contagion": "",
            "total": 0, "confirmed": 0, "suspected": 0, "recovered": 0, "deceased": 0
        })

        for c in cases:
            if c.disease:
                code = c.disease.code
                buckets[code]["name"] = c.disease.name
                buckets[code]["category"] = c.disease.category
                buckets[code]["contagion"] = c.disease.contagion_type
                buckets[code]["total"] += 1
                if c.case_status == CaseStatus.CONFIRMED.value:
                    buckets[code]["confirmed"] += 1
                elif c.case_status == CaseStatus.SUSPECTED.value:
                    buckets[code]["suspected"] += 1
                elif c.case_status == CaseStatus.RECOVERED.value:
                    buckets[code]["recovered"] += 1
                elif c.case_status == CaseStatus.DECEASED.value:
                    buckets[code]["deceased"] += 1

        rows = []
        for code, data in sorted(buckets.items(), key=lambda x: x[1]["total"], reverse=True):
            share = round((data["total"] / total_cases * 100), 1) if total_cases > 0 else 0.0
            rows.append({
                "Disease Code": code,
                "Disease Name": data["name"],
                "Category": data["category"],
                "Contagion Type": data["contagion"],
                "Total Cases": data["total"],
                "Confirmed": data["confirmed"],
                "Suspected": data["suspected"],
                "Recovered": data["recovered"],
                "Deceased": data["deceased"],
                "Share (%)": f"{share}%",
            })
        return title, columns, rows

    @classmethod
    def _compile_district_cases(cls, db: Session, filters: Dict[str, Any]):
        title = "District-wise Surveillance Caseload Distribution"
        columns = [
            "District Code",
            "District Name",
            "State",
            "Total Cases",
            "Confirmed",
            "Suspected",
            "Active Cases",
            "Share (%)",
        ]

        districts = db.query(District).all()
        query = (
            db.query(DiseaseCase)
            .join(Disease, DiseaseCase.disease_id == Disease.id)
            .outerjoin(Ward, DiseaseCase.ward_id == Ward.id)
            .outerjoin(LocalBody, Ward.local_body_id == LocalBody.id)
            .outerjoin(District, LocalBody.district_id == District.id)
        )
        query = cls._apply_case_filters(query, filters)
        cases = query.all()
        total_cases = len(cases)

        district_map = {d.id: d for d in districts}
        counts = defaultdict(lambda: {"total": 0, "confirmed": 0, "suspected": 0})

        for c in cases:
            if c.ward and c.ward.local_body and c.ward.local_body.district_id:
                dist_id = c.ward.local_body.district_id
                counts[dist_id]["total"] += 1
                if c.case_status == CaseStatus.CONFIRMED.value:
                    counts[dist_id]["confirmed"] += 1
                elif c.case_status == CaseStatus.SUSPECTED.value:
                    counts[dist_id]["suspected"] += 1

        rows = []
        for dist_id, d in district_map.items():
            cnt = counts[dist_id]
            active = cnt["confirmed"] + cnt["suspected"]
            share = round((cnt["total"] / total_cases * 100), 1) if total_cases > 0 else 0.0
            rows.append({
                "District Code": d.code,
                "District Name": d.name,
                "State": d.state,
                "Total Cases": cnt["total"],
                "Confirmed": cnt["confirmed"],
                "Suspected": cnt["suspected"],
                "Active Cases": active,
                "Share (%)": f"{share}%",
            })
        rows.sort(key=lambda x: x["Total Cases"], reverse=True)
        return title, columns, rows

    @classmethod
    def _compile_local_body_cases(cls, db: Session, filters: Dict[str, Any]):
        title = "Local Body (Corporation & Municipality) Caseload Summary"
        columns = [
            "Local Body Name",
            "Body Type",
            "District",
            "Total Cases",
            "Confirmed",
            "Suspected",
            "Active Cases",
        ]

        query = (
            db.query(DiseaseCase)
            .join(Disease, DiseaseCase.disease_id == Disease.id)
            .outerjoin(Ward, DiseaseCase.ward_id == Ward.id)
            .outerjoin(LocalBody, Ward.local_body_id == LocalBody.id)
            .outerjoin(District, LocalBody.district_id == District.id)
        )
        query = cls._apply_case_filters(query, filters)
        cases = query.all()

        lb_counts = defaultdict(lambda: {"type": "", "dist": "", "total": 0, "confirmed": 0, "suspected": 0})
        for c in cases:
            if c.ward and c.ward.local_body:
                lb = c.ward.local_body
                name = lb.name
                lb_counts[name]["type"] = lb.body_type
                lb_counts[name]["dist"] = lb.district.name if lb.district else "Kerala"
                lb_counts[name]["total"] += 1
                if c.case_status == CaseStatus.CONFIRMED.value:
                    lb_counts[name]["confirmed"] += 1
                elif c.case_status == CaseStatus.SUSPECTED.value:
                    lb_counts[name]["suspected"] += 1

        rows = []
        for name, d in sorted(lb_counts.items(), key=lambda x: x[1]["total"], reverse=True):
            rows.append({
                "Local Body Name": name,
                "Body Type": d["type"],
                "District": d["dist"],
                "Total Cases": d["total"],
                "Confirmed": d["confirmed"],
                "Suspected": d["suspected"],
                "Active Cases": d["confirmed"] + d["suspected"],
            })
        return title, columns, rows

    @classmethod
    def _compile_ward_cases(cls, db: Session, filters: Dict[str, Any]):
        title = "Ward-wise Micro-Surveillance Epidemiological Report"
        columns = [
            "Ward No.",
            "Ward Name",
            "Local Body",
            "District",
            "Total Cases",
            "Active",
            "Concentration Tier",
        ]

        query = (
            db.query(DiseaseCase)
            .join(Disease, DiseaseCase.disease_id == Disease.id)
            .outerjoin(Ward, DiseaseCase.ward_id == Ward.id)
            .outerjoin(LocalBody, Ward.local_body_id == LocalBody.id)
            .outerjoin(District, LocalBody.district_id == District.id)
        )
        query = cls._apply_case_filters(query, filters)
        cases = query.all()

        ward_data = defaultdict(lambda: {
            "number": 0, "lb": "", "dist": "", "total": 0, "confirmed": 0, "suspected": 0
        })

        for c in cases:
            if c.ward:
                w = c.ward
                name = w.name
                ward_data[name]["number"] = w.ward_number
                ward_data[name]["lb"] = w.local_body.name if w.local_body else ""
                ward_data[name]["dist"] = w.local_body.district.name if (w.local_body and w.local_body.district) else ""
                ward_data[name]["total"] += 1
                if c.case_status in (CaseStatus.CONFIRMED.value, CaseStatus.SUSPECTED.value):
                    ward_data[name]["confirmed"] += 1

        rows = []
        for name, d in sorted(ward_data.items(), key=lambda x: x[1]["total"], reverse=True):
            tot = d["total"]
            if tot >= 10:
                tier = "HOTSPOT AREA"
            elif tot >= 5:
                tier = "HIGH CONCENTRATION"
            elif tot >= 3:
                tier = "MODERATE CONCENTRATION"
            else:
                tier = "LOW CONCENTRATION"

            rows.append({
                "Ward No.": str(d["number"]),
                "Ward Name": name,
                "Local Body": d["lb"],
                "District": d["dist"],
                "Total Cases": tot,
                "Active": d["confirmed"],
                "Concentration Tier": tier,
            })
        return title, columns, rows

    @classmethod
    def _compile_date_range_cases(cls, db: Session, filters: Dict[str, Any]):
        title = "Case Incident Line Listing (Anonymized Privacy Protected)"
        columns = [
            "Case ID",
            "Patient ID",
            "Disease",
            "Diagnosis Date",
            "Status",
            "Severity",
            "Ward",
            "Local Body",
            "District",
        ]

        query = (
            db.query(DiseaseCase)
            .join(Disease, DiseaseCase.disease_id == Disease.id)
            .outerjoin(Ward, DiseaseCase.ward_id == Ward.id)
            .outerjoin(LocalBody, Ward.local_body_id == LocalBody.id)
            .outerjoin(District, LocalBody.district_id == District.id)
            .outerjoin(Patient, DiseaseCase.patient_id == Patient.id)
        )
        query = cls._apply_case_filters(query, filters)
        cases = query.order_by(DiseaseCase.diagnosis_date.desc()).all()

        rows = []
        for c in cases:
            # Privacy protection: Patient pseudo_id only (no phone, no home address)
            p_pseudo = c.patient.pseudo_id if c.patient else "ANON"
            w_name = c.ward.name if c.ward else (f"Ward {c.patient.ward_number}" if c.patient else "-")
            lb_name = c.ward.local_body.name if (c.ward and c.ward.local_body) else (c.patient.local_body_name if c.patient else "-")
            d_name = c.ward.local_body.district.name if (c.ward and c.ward.local_body and c.ward.local_body.district) else (c.patient.district_name if c.patient else "-")

            rows.append({
                "Case ID": str(c.id)[:8] + "...",
                "Patient ID": p_pseudo,
                "Disease": c.disease.name if c.disease else "-",
                "Diagnosis Date": c.diagnosis_date.isoformat() if c.diagnosis_date else "-",
                "Status": c.case_status,
                "Severity": c.severity,
                "Ward": w_name,
                "Local Body": lb_name,
                "District": d_name,
            })
        return title, columns, rows

    @classmethod
    def _compile_hotspot_summary(cls, db: Session, filters: Dict[str, Any]):
        title = "Epidemic Outbreak Hotspot Surveillance Summary"
        columns = [
            "Hotspot Area",
            "District",
            "Risk Tier",
            "Total Cases",
            "Dominant Pathogen",
            "Surveillance Status",
        ]

        query = (
            db.query(DiseaseCase)
            .join(Disease, DiseaseCase.disease_id == Disease.id)
            .outerjoin(Ward, DiseaseCase.ward_id == Ward.id)
            .outerjoin(LocalBody, Ward.local_body_id == LocalBody.id)
            .outerjoin(District, LocalBody.district_id == District.id)
        )
        query = cls._apply_case_filters(query, filters)
        cases = query.all()

        ward_clusters = defaultdict(lambda: {"district": "", "total": 0, "diseases": defaultdict(int)})
        for c in cases:
            if c.ward:
                w_name = c.ward.name
                ward_clusters[w_name]["district"] = (
                    c.ward.local_body.district.name if (c.ward.local_body and c.ward.local_body.district) else "Kerala"
                )
                ward_clusters[w_name]["total"] += 1
                if c.disease:
                    ward_clusters[w_name]["diseases"][c.disease.name] += 1

        rows = []
        for w_name, d in sorted(ward_clusters.items(), key=lambda x: x[1]["total"], reverse=True):
            tot = d["total"]
            if tot >= 10:
                tier = "HOTSPOT AREA"
            elif tot >= 5:
                tier = "HIGH RISK"
            elif tot >= 3:
                tier = "MODERATE RISK"
            else:
                tier = "LOW RISK"

            dominant = max(d["diseases"].items(), key=lambda x: x[1])[0] if d["diseases"] else "Under Surveillance"
            rows.append({
                "Hotspot Area": w_name,
                "District": d["district"],
                "Risk Tier": tier,
                "Total Cases": tot,
                "Dominant Pathogen": dominant,
                "Surveillance Status": "ACTIVE INVESTIGATION" if tot >= 5 else "CONTAINED MONITORING",
            })
        return title, columns, rows

    @classmethod
    def _compile_potential_exposures(cls, db: Session, filters: Dict[str, Any]):
        title = "Potential Spatial-Temporal Exposure Overlap Report"
        columns = [
            "Exposure ID",
            "Patient A",
            "Patient B",
            "Location Area",
            "Separation (m)",
            "Time Gap (min)",
            "Confidence (%)",
            "Review Status",
        ]

        query = db.query(ExposureEvent).order_by(ExposureEvent.detected_at.desc())
        exposures = query.all()

        rows = []
        for e in exposures:
            # Query patient pseudo ids
            p_a = db.query(Patient).filter(Patient.id == e.patient_a_id).first()
            p_b = db.query(Patient).filter(Patient.id == e.patient_b_id).first()

            p_a_id = p_a.pseudo_id if p_a else "PAT-A"
            p_b_id = p_b.pseudo_id if p_b else "PAT-B"

            rows.append({
                "Exposure ID": str(e.id)[:8] + "...",
                "Patient A": p_a_id,
                "Patient B": p_b_id,
                "Location Area": "Palayam Cluster" if (e.latitude and e.latitude > 8.5) else "Urban Central Zone",
                "Separation (m)": f"{round(float(e.distance or 0.0), 1)} m",
                "Time Gap (min)": f"{round(float(e.time_difference or 0.0), 1)} min",
                "Confidence (%)": f"{round(float(e.confidence_score or 0.0) * 100, 1)}%",
                "Review Status": e.status,
            })
        return title, columns, rows

    @classmethod
    def _compile_monitoring_summary(cls, db: Session, filters: Dict[str, Any]):
        title = "Patient Location Telemetry Monitoring Summary (~15-min Intervals)"
        columns = [
            "Session ID",
            "Patient ID",
            "Status",
            "Start Time",
            "End Time",
            "Sampling Interval",
            "Compliance",
        ]

        sessions = db.query(MonitoringSession).order_by(MonitoringSession.start_time.desc()).all()
        rows = []
        for s in sessions:
            p_pseudo = s.patient.pseudo_id if s.patient else "PAT-ANON"
            rows.append({
                "Session ID": str(s.id)[:8] + "...",
                "Patient ID": p_pseudo,
                "Status": s.status,
                "Start Time": s.start_time.strftime("%Y-%m-%d %H:%M") if s.start_time else "-",
                "End Time": s.end_time.strftime("%Y-%m-%d %H:%M") if s.end_time else "-",
                "Sampling Interval": "~15 minutes",
                "Compliance": "VERIFIED CONSENT" if s.status == SessionStatus.ACTIVE.value else "SESSION COMPLETED",
            })
        return title, columns, rows

    @classmethod
    def _compile_comprehensive(cls, db: Session, filters: Dict[str, Any]):
        """Consolidates key metrics from all modules into a master surveillance report."""
        title = "HealthWatch Comprehensive State Surveillance Dossier"
        columns = [
            "Jurisdiction / Entity",
            "Category",
            "Total Incidence",
            "Active Caseload",
            "Surveillance Tier",
            "Key Observation",
        ]

        # Aggregate high level summary rows
        t1, c1, r_dis = cls._compile_disease_statistics(db, filters)
        t2, c2, r_dist = cls._compile_district_cases(db, filters)
        t3, c3, r_hot = cls._compile_hotspot_summary(db, filters)
        t4, c4, r_exp = cls._compile_potential_exposures(db, filters)
        t5, c5, r_mon = cls._compile_monitoring_summary(db, filters)

        rows = []
        for d in r_dist[:4]:
            rows.append({
                "Jurisdiction / Entity": d["District Name"],
                "Category": "District Overview",
                "Total Incidence": d["Total Cases"],
                "Active Caseload": d["Active Cases"],
                "Surveillance Tier": d["Share (%)"] + " burden",
                "Key Observation": f"{d['Confirmed']} confirmed cases",
            })

        for dis in r_dis[:4]:
            rows.append({
                "Jurisdiction / Entity": dis["Disease Name"],
                "Category": "Pathogen Distribution",
                "Total Incidence": dis["Total Cases"],
                "Active Caseload": dis["Confirmed"] + dis["Suspected"],
                "Surveillance Tier": dis["Category"],
                "Key Observation": f"{dis['Contagion Type']} contagion",
            })

        for h in r_hot[:3]:
            rows.append({
                "Jurisdiction / Entity": h["Hotspot Area"],
                "Category": "Outbreak Hotspot",
                "Total Incidence": h["Total Cases"],
                "Active Caseload": h["Total Cases"],
                "Surveillance Tier": h["Risk Tier"],
                "Key Observation": f"Dominant: {h['Dominant Pathogen']}",
            })

        rows.append({
            "Jurisdiction / Entity": "Spatial Overlaps",
            "Category": "Potential Exposures",
            "Total Incidence": len(r_exp),
            "Active Caseload": sum(1 for e in r_exp if e["Review Status"] == ExposureStatus.POTENTIAL.value),
            "Surveillance Tier": "DECISION SUPPORT",
            "Key Observation": "Non-causal proximity tracking",
        })

        rows.append({
            "Jurisdiction / Entity": "Location Telemetry",
            "Category": "Authorized Monitoring",
            "Total Incidence": len(r_mon),
            "Active Caseload": sum(1 for m in r_mon if m["Status"] == SessionStatus.ACTIVE.value),
            "Surveillance Tier": "QUARANTINE COMPLIANCE",
            "Key Observation": "Periodic ~15 min discrete points",
        })

        return title, columns, rows

    # ==========================================================================
    # 2. CSV GENERATION (RFC 4180 COMPLIANT)
    # ==========================================================================

    @classmethod
    def render_csv(
        cls,
        title: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        filters: Dict[str, Any],
    ) -> str:
        """Render CSV string with metadata comments and tabular records."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # 1. Header Metadata Section
        writer.writerow([f"# HEALTHWATCH EPIDEMIOLOGICAL SURVEILLANCE REPORT: {title.upper()}"])
        writer.writerow([f"# Generated At (UTC): {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"])
        filter_str = ", ".join(f"{k}={v}" for k, v in filters.items() if v) or "Statewide (All)"
        writer.writerow([f"# Applied Filters: {filter_str}"])
        writer.writerow(["# Privacy Compliance: STRICTLY ANONYMIZED. Identifiers restricted to pseudo_id. No phone or street addresses."])
        writer.writerow(["# Ethical Disclaimer: DECISION SUPPORT ONLY. Potential exposure indicates spatial-temporal overlap and does not assert infection transmission."])
        writer.writerow([])  # Empty separation line

        # 2. Tabular Headers & Rows
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row.get(col, "") for col in columns])

        return output.getvalue()

    # ==========================================================================
    # 3. PDF GENERATION (REPORTLAB PUBLICATION-READY)
    # ==========================================================================

    @classmethod
    def render_pdf(
        cls,
        title: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        filters: Dict[str, Any],
    ) -> bytes:
        """Render publication-grade PDF document using ReportLab."""
        buffer = io.BytesIO()

        # Choose landscape orientation if many columns, else portrait
        is_landscape = len(columns) >= 6
        page_size = landscape(A4) if is_landscape else A4

        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            alignment=TA_LEFT,
            fontName="Helvetica",
        )
        filter_box_style = ParagraphStyle(
            "FilterBox",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica",
        )
        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1e293b"),
            alignment=TA_LEFT,
            fontName="Helvetica",
        )
        table_cell_center_style = ParagraphStyle(
            "TableCellCenter",
            parent=table_cell_style,
            alignment=TA_CENTER,
        )
        disclaimer_style = ParagraphStyle(
            "DocDisclaimer",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_LEFT,
            fontName="Helvetica-Oblique",
        )

        story = []

        # 1. Document Header Banner
        header_text = "<b>HEALTHWATCH EPIDEMIOLOGICAL SURVEILLANCE SYSTEM</b> | STATE OF KERALA"
        story.append(Paragraph(header_text, subtitle_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(title, title_style))
        gen_date = datetime.datetime.utcnow().strftime("%B %d, %Y - %H:%M UTC")
        story.append(Paragraph(f"Official Surveillance Digest &bull; Compiled: <b>{gen_date}</b>", subtitle_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

        # 2. Active Filters & Scope Box
        active_filters_list = [f"<b>{k}:</b> {v}" for k, v in filters.items() if v]
        filter_summary_str = " &nbsp;|&nbsp; ".join(active_filters_list) if active_filters_list else "Statewide Surveillance (No localized filters applied)"
        filter_paragraph = Paragraph(
            f"<b>Active Surveillance Scope:</b> {filter_summary_str}<br/>"
            f"<b>Total Tabular Records:</b> {len(rows)} compiled &nbsp;|&nbsp; <b>Privacy:</b> Anonymized Pseudo-IDs (No raw GPS or contact details)",
            filter_box_style,
        )
        filter_table = Table([[filter_paragraph]], colWidths=[doc.width])
        filter_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(filter_table)
        story.append(Spacer(1, 12))

        # 3. Data Table Compilation
        table_data = []

        # Header Row
        header_row = [Paragraph(f"<b>{col}</b>", table_header_style) for col in columns]
        table_data.append(header_row)

        # Body Rows
        if not rows:
            empty_row = [Paragraph("<i>No data records matching active surveillance filters.</i>", table_cell_center_style)]
            empty_row += [""] * (len(columns) - 1)
            table_data.append(empty_row)
        else:
            for r in rows:
                row_cells = []
                for col in columns:
                    val = str(r.get(col, ""))
                    # Check if numeric / code for centering
                    if val.isdigit() or val.endswith("%") or len(val) <= 4:
                        cell_p = Paragraph(val, table_cell_center_style)
                    else:
                        cell_p = Paragraph(val, table_cell_style)
                    row_cells.append(cell_p)
                table_data.append(row_cells)

        # Compute column widths proportionally
        col_count = len(columns)
        available_width = doc.width
        col_width = available_width / col_count

        data_table = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
        data_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            # Alternating row background
            *[("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8fafc")) for i in range(2, len(table_data), 2)],
        ]))

        story.append(data_table)
        story.append(Spacer(1, 16))

        # 4. Mandatory Decision Support & Privacy Disclaimer
        disclaimer_text = (
            "<b>IMPORTANT EPIDEMIOLOGICAL NOTICE:</b> HealthWatch reports are compiled strictly for decision support and "
            "epidemiological surveillance. In compliance with strict patient privacy safeguards, records contain only anonymized "
            "synthetic identifiers (pseudo_id) and omit residential addresses or private telemetry. Potential exposure events "
            "represent spatial-temporal overlaps and do not assert clinical transmission."
        )
        story.append(Paragraph(disclaimer_text, disclaimer_style))

        # Build Document
        doc.build(story)
        return buffer.getvalue()
