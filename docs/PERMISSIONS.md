# Role permission matrix

The signed-in user's `role` and `center` decide access. Django groups mirror the roles, but a group permission is not enough to cross a center or to let the super admin run a center's day. Querysets are filtered before an object is loaded, so another center's id is a 404 rather than a readable record.

| Capability | Super Admin | Center Manager | Finance Manager | Teacher | Student |
| --- | --- | --- | --- | --- | --- |
| View all centers | Yes | Own center | Own center | Own center | Own center |
| Create or edit a center | Yes | No | No | No | No |
| Assign the center manager | Yes | No | No | No | No |
| Global settings | Yes | No | No | No | No |
| Center settings | Read | Write | Read | No | No |
| Create courses, classes, rooms, schedules | No | Yes | No | No | No |
| View courses | All centers | Own center | Own center via invoices | Assigned | Own center, active |
| Create finance manager, teacher, student | No | Own center | No | No | No |
| Create a center manager | Yes | No | No | No | No |
| Staff contracts | Assign manager | Teachers and finance | Read own | Read own | No |
| Enroll a student | No | Manual | No | No | Self, when allowed |
| Approve a pending enrollment | No | Yes | No | No | No |
| Mark attendance | No | No | No | Own classes | No |
| Correct attendance | No | Yes | No | No | No |
| Record payments, plans, scholarships | No | Read | Yes | No | Read own |
| Request a refund | No | No | Yes | No | Own invoices |
| Approve or reject a refund | No | Yes | No | No | No |
| Prepare a finance report | No | Read | Yes | No | No |
| Send a report to super admin | Read | Yes | No | No | No |
| Edit own profile and photo | Yes | Yes | Yes | Yes | Yes |

Inactive users and inactive centers cannot perform operational writes. A staff member without an active contract cannot either. Students do not have contracts.
