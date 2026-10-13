from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


output = Path("data/sample_corpus/workplace_guidelines.pdf")
output.parent.mkdir(parents=True, exist_ok=True)

pdf = canvas.Canvas(str(output), pagesize=letter)

pdf.setTitle("Workplace Guidelines")
pdf.drawString(72, 750, "Workplace Guidelines")
pdf.drawString(72, 720, "Employees should maintain a respectful workplace.")
pdf.drawString(72, 690, "Company documents should be handled responsibly.")

pdf.save()

print(f"Created sample PDF: {output}")