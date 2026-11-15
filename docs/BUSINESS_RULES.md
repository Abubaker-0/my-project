# Business rules

These rules are enforced in the service layer and, where practical, by database constraints. The interface repeats the same limits so a form fails before the request when it can.

## Centers and contracts

- A center has one active center manager. The lock is a unique nullable column on the active contract, so a second active manager cannot be saved.
- A manager, finance manager, or teacher has at most one active contract. A new contract is allowed after the previous one is expired or terminated.
- Contract length is yearly (364–366 days) or six months (178–186 days).
- Salary is hourly or monthly and must be greater than zero. Payment of that salary is cash or bank.
- Replacing a manager ends the previous contract and opens the new one in one transaction.
- An active center is not left without a manager unless the center is deactivated or the manager is replaced.
- The available-manager list excludes anyone with an active contract.

## People

- Gender is male or female.
- A student, teacher, finance manager, and center manager belong to one center.
- Super admin has no center.
- A teacher cannot teach at a second center while the contract is active.

## Courses, classes, enrollment

- Only the center manager creates courses, classes, rooms, and schedules. Creating a course also creates the first section and at least one meeting.
- A schedule must not overlap for the teacher, the classroom, or an enrolled student. Back-to-back times are allowed.
- A student enrolls in more than one course in the same center, and in no course at another center.
- Self-enrollment requires the student's center, an active course, remaining seats, no existing open enrollment, and the center setting that allows it. If approval is required, the enrollment stays pending and still holds a seat.
- The manager can enroll manually when self-enrollment is off. Capacity, duplicates, clashes, and the center boundary still apply.
- Remaining capacity is the capacity minus pending and active enrollments. It cannot go below zero.
- Fee changes do not rewrite invoices that were already issued.

## Attendance

- Status is present or absent.
- The teacher of that class submits the date. The date must be a real meeting day, not in the future, and inside the course dates.
- The submission must include every active student once.
- After submission, only the center manager can change a mark.

## Money

- Payment methods are cash and bank. Bank payments require a reference of at least three characters.
- There is no exchange rate and no reconciliation.
- An invoice is created when an enrollment becomes active. Outstanding is the payable fee minus payments, and it does not go below zero. A refund does not put the student back into debt.
- Scholarships are a percentage from 0 to 100 or a fixed amount that cannot exceed the fee. They are applied before any payment. An existing unpaid installment plan is redistributed.
- Installments are 1 to 3, also capped by the global setting and the center setting. Due dates are unique and in order. The amounts add up to the payable fee.
- Status is pending, partially paid, paid, or overdue. A past due date that is not fully paid is overdue.
- A student requests a refund on their own invoice. Finance can request one for the center. Only the center manager approves or rejects it.

## Reports

- The live dashboard reads current rows and stays inside the caller's center.
- An official report freezes a snapshot. Finance prepares it and submits it to the manager. The manager sends it to the super admin.
- Expected revenue, scholarships, and outstanding follow invoices in the period. Collected payments and refunds follow their own dates.

## Security

- Another center's identifier is not readable.
- A body that names a different center is rejected and audited.
- Passwords are validated by Django's validators. Reset tokens are stored as hashes. In debug mode the raw token is returned so a local demo can finish without email.
