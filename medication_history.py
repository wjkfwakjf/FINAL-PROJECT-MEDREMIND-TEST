from tkinter import ttk


class MedicationHistoryFeature:
    def _create_tab_history(self, notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=self.tabs[4])

        history_box = ttk.LabelFrame(frame, text="Medication History", padding=10)
        history_box.pack(fill="both", expand=True, padx=12, pady=12)

        cols = ("Recorded At", "Patient", "Medicine", "Dosage", "Time", "Status")
        self.history_tree = ttk.Treeview(history_box, columns=cols, show="headings")
        for col in cols:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150, anchor="center")
        self.history_tree.pack(fill="both", expand=True)

    def _refresh_history_tree(self) -> None:
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        conn = self._connect()
        try:
            history = conn.execute(
                """
                SELECT id, patient_name, medicine_name, dosage, reminder_time, status, recorded_at
                FROM medication_history
                ORDER BY recorded_at DESC, id DESC
                """
            ).fetchall()
        finally:
            conn.close()
        for event in history:
            self.history_tree.insert(
                "",
                "end",
                values=(
                    event["recorded_at"],
                    event["patient_name"],
                    event["medicine_name"],
                    event["dosage"],
                    event["reminder_time"],
                    event["status"],
                ),
            )
