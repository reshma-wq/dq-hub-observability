from openpyxl import Workbook
from datetime import datetime
import os

class ReportService:

    def generate_excel_report(self, run_id, results):
        wb = Workbook()

        # Sheet 1 - Summary
        ws = wb.active
        ws.title = "Summary"

        total_rules = len(results)
        failed_rules = len(
            [r for r in results if str(r.get("status", "")).upper() == "FAIL"]
        )

        ws.append(["Metric", "Value"])
        ws.append(["Run ID", run_id])
        ws.append(["Total Rules", total_rules])
        ws.append(["Failed Rules", failed_rules])
        ws.append(["Generated At", str(datetime.utcnow())])

        # Sheet 2 - Detailed Results
        detail_sheet = wb.create_sheet("Results")

        if results:
            headers = list(results[0].keys())
            detail_sheet.append(headers)

            for row in results:
                detail_sheet.append(
                    [row.get(col, "") for col in headers]
                )

        os.makedirs("reports", exist_ok=True)

        file_path = f"reports/{run_id}.xlsx"
        wb.save(file_path)

        return file_path