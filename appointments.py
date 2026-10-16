from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Sequence


@dataclass
class Patient:
    id: int
    full_name: str
    age: int
    contact: str


@dataclass
class Doctor:
    id: int
    name: str
    specialty: str | None = None


@dataclass
class Appointment:
    id: int
    patient_id: int
    patient_name: str
    doctor_id: int | None
    doctor_name: str | None
    appointment_date: date
    reason: str = "Follow-up"


class AppointmentDashboard:
    """A simple appointment manager for MedRemind Care."""

    def __init__(
        self,
        patients: Sequence[Patient] | None = None,
        doctors: Sequence[Doctor] | None = None,
        appointments: Sequence[Appointment] | None = None,
    ) -> None:
        self.patients: List[Patient] = list(patients or [])
        self.doctors: List[Doctor] = list(doctors or [])
        self.appointments: List[Appointment] = list(appointments or [])

    def find_patient(self, patient_id: int) -> Patient | None:
        for patient in self.patients:
            if patient.id == patient_id:
                return patient
        return None

    def find_doctor(self, doctor_id: int | None) -> Doctor | None:
        if doctor_id is None:
            return None
        for doctor in self.doctors:
            if doctor.id == doctor_id:
                return doctor
        return None

    def schedule_appointment(
        self,
        patient_id: int,
        appointment_date: date,
        doctor_id: int | None = None,
        reason: str = "Follow-up",
    ) -> Appointment:
        patient = self.find_patient(patient_id)
        if patient is None:
            raise ValueError(f"Patient with id {patient_id} was not found.")

        doctor = self.find_doctor(doctor_id)
        appointment = Appointment(
            id=self._next_id(),
            patient_id=patient.id,
            patient_name=patient.full_name,
            doctor_id=doctor.id if doctor else None,
            doctor_name=doctor.name if doctor else "Unassigned",
            appointment_date=appointment_date,
            reason=reason.strip() or "Follow-up",
        )
        self.appointments.append(appointment)
        return appointment

    def _next_id(self) -> int:
        if not self.appointments:
            return 1
        return max(item.id for item in self.appointments) + 1

    def render_dashboard(self) -> str:
        upcoming = sorted(self.appointments, key=lambda item: item.appointment_date)

        lines = [
            "MedRemind Care - Appointments Dashboard",
            "=" * 38,
            f"Patients: {len(self.patients)}",
            f"Doctors: {len(self.doctors)}",
            f"Scheduled appointments: {len(self.appointments)}",
            "",
            "Schedule an appointment",
            "-" * 22,
            self._format_patient_list(),
            "",
            "All appointments",
            self._format_appointments(upcoming),
        ]
        return "\n".join(lines)

    def _format_patient_list(self) -> str:
        if not self.patients:
            return "No patients available. Register a patient before scheduling an appointment."

        rows = [
            [str(patient.id), patient.full_name, str(patient.age), patient.contact]
            for patient in self.patients
        ]
        return self._format_table(["ID", "Name", "Age", "Contact"], rows)

    def _format_appointments(self, appointments: Sequence[Appointment]) -> str:
        if not appointments:
            return "No appointments scheduled yet."

        rows = [
            [
                appointment.appointment_date.isoformat(),
                appointment.patient_name,
                appointment.doctor_name or "—",
                appointment.reason,
            ]
            for appointment in appointments
        ]
        return self._format_table(["Date", "Patient", "Doctor", "Reason"], rows)

    @staticmethod
    def _format_table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
        rows = [list(row) for row in rows]
        widths = [len(str(header)) for header in headers]

        for row in rows:
            for index, value in enumerate(row):
                widths[index] = max(widths[index], len(str(value)))

        def render_line(items: Sequence[str]) -> str:
            return " | ".join(str(item).ljust(widths[index]) for index, item in enumerate(items))

        table = [render_line(headers), "-+-".join("-" * width for width in widths)]
        table.extend(render_line(row) for row in rows)
        return "\n".join(table)


def build_demo_data() -> AppointmentDashboard:
    patients = [
        Patient(1, "Grace Eze", 28, "+2348098765432"),
    ]

    doctors = [
        Doctor(1, "Dr. Smith", "Cardiology"),
        Doctor(2, "Dr. Nwosu", "General Medicine"),
        Doctor(3, "Dr. Ali", "Family Practice"),
    ]

    appointments = [
        Appointment(1, 1, "Grace Eze", 3, "Dr. Ali", date(2026, 10, 8), "Medication review"),
    ]

    dashboard = AppointmentDashboard(patients=patients, doctors=doctors, appointments=appointments)
    return dashboard


def main() -> int:
    dashboard = build_demo_data()
    dashboard.schedule_appointment(
        patient_id=1,
        appointment_date=date(2026, 10, 12),
        doctor_id=2,
        reason="Follow-up consult",
    )
    print(dashboard.render_dashboard())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
