from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List, Sequence


@dataclass
class Patient:
    id: int
    full_name: str
    age: int
    contact: str
    status: str = "active"


@dataclass
class Medicine:
    id: int
    patient_id: int
    patient_name: str
    name: str
    dosage: str
    active: bool = True


@dataclass
class Appointment:
    id: int
    patient_id: int
    patient_name: str
    appointment_date: date
    doctor_name: str
    reason: str = "Follow-up"


@dataclass
class AdherenceSummary:
    taken: int = 0
    missed: int = 0
    pending: int = 0

    @property
    def total(self) -> int:
        return self.taken + self.missed + self.pending

    def percent(self, value: int) -> float:
        if self.total == 0:
            return 0.0
        return (value / self.total) * 100


class AdminDashboard:
    """Simple model for the MedRemind Care admin overview."""

    def __init__(
        self,
        patients: Sequence[Patient] | None = None,
        medicines: Sequence[Medicine] | None = None,
        appointments: Sequence[Appointment] | None = None,
    ) -> None:
        self.patients: List[Patient] = list(patients or [])
        self.medicines: List[Medicine] = list(medicines or [])
        self.appointments: List[Appointment] = list(appointments or [])

    @property
    def adherence(self) -> AdherenceSummary:
        return AdherenceSummary(
            taken=128,
            missed=42,
            pending=18,
        )

    @property
    def total_patients(self) -> int:
        return len(self.patients)

    @property
    def total_medicines(self) -> int:
        return len(self.medicines)

    @property
    def active_medicines(self) -> int:
        return sum(1 for medicine in self.medicines if medicine.active)

    @property
    def recent_appointments(self) -> List[Appointment]:
        return sorted(self.appointments, key=lambda item: item.appointment_date, reverse=True)

    def render_summary(self) -> str:
        summary = self.adherence
        lines = [
            "MedRemind Care - Admin Dashboard",
            "=" * 32,
            f"Patients: {self.total_patients}",
            f"Medicines: {self.total_medicines}  |  Active: {self.active_medicines}",
            f"Appointments: {len(self.appointments)}",
            "",
            "Adherence Overview (all time)",
            f"  Taken:   {summary.taken:>3}  ({summary.percent(summary.taken):>5.1f}%)",
            f"  Missed:  {summary.missed:>3}  ({summary.percent(summary.missed):>5.1f}%)",
            f"  Pending: {summary.pending:>3}  ({summary.percent(summary.pending):>5.1f}%)",
            "",
            "Patients",
            self._format_table(
                ["Name", "Age", "Contact", "Status"],
                [
                    [patient.full_name, str(patient.age), patient.contact, patient.status.title()]
                    for patient in self.patients
                ],
            ),
            "",
            "Recent Appointments",
            self._format_table(
                ["Date", "Patient", "Doctor", "Reason"],
                [
                    [
                        item.appointment_date.isoformat(),
                        item.patient_name,
                        item.doctor_name,
                        item.reason,
                    ]
                    for item in self.recent_appointments[:5]
                ],
            ),
        ]
        return "\n".join(lines)

    @staticmethod
    def _format_table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
        rows = [list(row) for row in rows]
        widths = [len(str(header)) for header in headers]

        for row in rows:
            for index, value in enumerate(row):
                widths[index] = max(widths[index], len(str(value)))

        def line(items: Sequence[str]) -> str:
            return " | ".join(str(item).ljust(widths[index]) for index, item in enumerate(items))

        table = [line(headers), "-+-".join("-" * width for width in widths)]
        table.extend(line(row) for row in rows)
        return "\n".join(table)


def build_demo_data() -> AdminDashboard:
    patients = [
        Patient(1, "Grace Eze", 28, "+2348098765432", "monitoring"),
    ]

    medicines = [
        Medicine(1, 1, "Grace Eze", "Ibuprofen", "200mg", False),
    ]

    appointments = [
        Appointment(1, 1, "Grace Eze", date(2026, 9, 22), "Dr. Ali", "Medication review"),
    ]

    return AdminDashboard(patients=patients, medicines=medicines, appointments=appointments)


def main() -> int:
    dashboard = build_demo_data()
    print(dashboard.render_summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
