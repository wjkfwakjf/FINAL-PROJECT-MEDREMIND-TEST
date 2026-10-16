from datetime import datetime
from tkinter import messagebox, ttk


class MedicineRemindersFeature:
    def _check_medication_alerts(self) -> None:
        now = datetime.now()
        today = now.date().isoformat()
        current_time = now.strftime("%H:%M")
        due_medicines = []
        for medicine in self.get_pending_reminders():
            reminder_time = medicine["reminder_time"]
            if not reminder_time or reminder_time > current_time:
                continue
            notification_key = (int(medicine["id"]), today)
            if notification_key in self._notified_reminders:
                continue
            self._notified_reminders.add(notification_key)
            due_medicines.append(medicine)
        if due_medicines:
            reminder_lines = [
                f"{medicine['medicine_name']} ({medicine['dosage']}) - {medicine['patient_name']}"
                for medicine in due_medicines
            ]
            messagebox.showinfo(
                "Medicine reminder",
                "It's time for:\n" + "\n".join(reminder_lines),
            )
        self.root.after(30000, self._check_medication_alerts)

    def _create_tab_reminders(self, notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=self.tabs[2])

        reminder_box = ttk.LabelFrame(frame, text="Medication Reminders", padding=10)
        reminder_box.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(
            reminder_box,
            text="Only medicines still waiting to be recorded appear here.",
        ).pack(anchor="w", pady=(0, 8))
        cols = ("ID", "Patient", "Medicine", "Dosage", "Time", "Status")
        self.reminder_tree = ttk.Treeview(reminder_box, columns=cols, show="headings", height=15)
        for col in cols:
            self.reminder_tree.heading(col, text=col)
            self.reminder_tree.column(col, width=130, anchor="center")
        self.reminder_tree.pack(fill="both", expand=True)

        controls = ttk.Frame(reminder_box)
        controls.pack(fill="x", pady=(10, 0))

        ttk.Button(controls, text="Mark as Taken", command=lambda: self.update_medicine_status("taken")).pack(side="left", padx=5)
        ttk.Button(controls, text="Mark as Missed", command=lambda: self.update_medicine_status("missed")).pack(side="left", padx=5)

    def _refresh_reminders(self) -> None:
        for row in self.reminder_tree.get_children():
            self.reminder_tree.delete(row)
        for med in self.get_pending_reminders():
            self.reminder_tree.insert(
                "",
                "end",
                iid=str(med["id"]),
                values=(
                    med["id"],
                    med["patient_name"],
                    med["medicine_name"],
                    med["dosage"],
                    med["reminder_time"],
                    "pending",
                ),
            )

    def update_medicine_status(self, status: str) -> None:
        if status not in {"taken", "missed"}:
            raise ValueError("Medicine status must be 'taken' or 'missed'.")
        selection = self.reminder_tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Select a pending medicine reminder to update its status.")
            return

        medicine_id = int(selection[0])
        conn = self._connect()
        try:
            medicine = conn.execute(
                """
                SELECT m.*, p.full_name AS patient_name
                FROM medicines m
                JOIN patients p ON p.id = m.patient_id
                WHERE m.id = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM medication_history h
                      WHERE h.medicine_id = m.id AND h.dose_date = ?
                  )
                """,
                (medicine_id, datetime.now().date().isoformat()),
            ).fetchone()
            if medicine is None:
                messagebox.showerror("Not found", "The selected pending medicine could not be found.")
                return

            conn.execute("UPDATE medicines SET status = ? WHERE id = ?", (status, medicine_id))
            conn.execute(
                """
                INSERT INTO medication_history
                    (medicine_id, patient_id, patient_name, medicine_name, dosage, reminder_time,
                     status, dose_date, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    medicine["id"],
                    medicine["patient_id"],
                    medicine["patient_name"],
                    medicine["medicine_name"],
                    medicine["dosage"],
                    medicine["reminder_time"],
                    status,
                    datetime.now().date().isoformat(),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        self.refresh_all()
        messagebox.showinfo("Updated", f"Medication marked as {status}; it has been removed from pending reminders.")
