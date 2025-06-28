from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import datetime
import textwrap

from analysis.plot_summary_table import plot_summary_table_to_buffer

def generate_one_pager(
    filename,
    user_name,
    user_email,
    orbit_label,
    mission_params,
    cost_summary,
    performance_summary,
    summary_table_df=None,
    thermal_summary=None,
    rf_summary=None,
    disclaimer=None,
    logo_path=None,
    plot_fig_width=9,
    plot_fig_height_per_row=1.5,
    plot_height_in_pdf=3.6*inch,
    thermal_plot_buf=None,
):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    margin = 0.75 * inch
    line_y = height - margin

    # Header/logo
    if logo_path:
        c.drawImage(logo_path, margin, line_y - 0.75*inch, width=1.5*inch, height=0.5*inch, mask='auto')
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin + (1.7*inch if logo_path else 0), line_y, "In-Situ Compute | Bitcoin Mining Mission Cost Study")
    c.setFont("Helvetica", 10)
    c.drawString(margin, line_y - 0.3*inch, f"Generated for: {user_name} ({user_email})")
    c.drawString(margin, line_y - 0.5*inch, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Orbit summary
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, line_y - 1.1*inch, f"Orbit: {orbit_label}")

    # Mission Parameters
    c.setFont("Helvetica", 10)
    y = line_y - 1.35*inch
    c.drawString(margin, y, "Mission Parameters:")
    y -= 0.18*inch
    for k, v in mission_params.items():
        if isinstance(v, float):
            v = f"{v:.3f}"  # Truncate to 3 decimal places
        c.drawString(margin + 0.15*inch, y, f"- {k}: {v}")
        y -= 0.16*inch

    # Key Results
    y -= 0.08*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Key Results:")
    y -= 0.17*inch
    c.setFont("Helvetica", 10)
    for k, v in performance_summary.items():
        c.drawString(margin + 0.15*inch, y, f"{k}: {v}")
        y -= 0.16*inch

    # Cost Summary
    y -= 0.08*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Cost Summary:")
    y -= 0.17*inch
    c.setFont("Helvetica", 10)
    for k, v in cost_summary.items():
        c.drawString(margin + 0.15*inch, y, f"{k}: {v}")
        y -= 0.16*inch

    # Thermal Summary
    if thermal_summary:
        y -= 0.08*inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y, "Thermal Summary:")
        y -= 0.17*inch
        c.setFont("Helvetica", 10)
        for k, v in thermal_summary.items():
            c.drawString(margin + 0.15*inch, y, f"{k}: {v}")
            y -= 0.16*inch

    # RF Summary
    if rf_summary:
        y -= 0.08*inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y, "RF Link Summary:")
        y -= 0.17*inch
        c.setFont("Helvetica", 10)
        for k, v in rf_summary.items():
            c.drawString(margin + 0.15*inch, y, f"{k}: {v}")
            y -= 0.16*inch

    # Bar chart placement
    chart_height = plot_height_in_pdf
    disclaimer_height = 0.45 * inch
    bottom_padding = 0.3 * inch
    chart_y = margin + disclaimer_height + 2 * bottom_padding
    chart_x = margin * 2
    chart_width = width - 3 * margin

    if summary_table_df is not None:
        plot_buf = plot_summary_table_to_buffer(
            summary_table_df,
            fig_width=plot_fig_width,
            fig_height_per_row=plot_fig_height_per_row
        )
        summary_img = ImageReader(plot_buf)
        c.drawImage(
            summary_img,
            chart_x*1.5,
            chart_y,
            width=chart_width,
            height=chart_height,
            preserveAspectRatio=True,
            mask='auto'
        )
        c.rect(chart_x*2.3, chart_y, chart_width*0.6, chart_height)

    # Thermal plot placement
    if thermal_plot_buf:
        thermal_img = ImageReader(thermal_plot_buf)
        thermal_img_width = 4.5 * inch
        thermal_img_height = 4.5 * inch
        thermal_plot_x = width - thermal_img_width - margin
        thermal_plot_y = height - margin - 5.25 * inch
        c.drawImage(
            thermal_img,
            thermal_plot_x,
            thermal_plot_y,
            width=thermal_img_width,
            height=thermal_img_height,
            preserveAspectRatio=True,
            mask='auto'
        )
        c.rect(thermal_plot_x, thermal_plot_y*1.08, thermal_img_width, thermal_img_height*0.82)

    # Disclaimer at bottom
    if not disclaimer:
        disclaimer = (
            "This report provides an approximate cost and technical summary for your requested mission profile. "
            "Values are estimates only, subject to change, and do not constitute a binding quote or proposal. "
            "Contact us for a detailed feasibility study."
        )

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)

    wrapped_lines = textwrap.wrap(disclaimer, width=110)
    line_height = 10
    total_text_height = len(wrapped_lines) * line_height
    y_position = margin + total_text_height

    for line in wrapped_lines:
        c.drawString(margin, y_position, line)
        y_position -= line_height

    c.showPage()
    c.save()
