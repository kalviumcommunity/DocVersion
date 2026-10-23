# Citation Verification Example

This report checks that each citation points to a real chunk and that the retrieved text matches the original corpus.

## Example citation: [1]

- Verified: **True**
- Source: `leave_policy.md`
- Chunk ID: `leave_policy_chunk_001`
- Section: `Annual Leave`

### Original text used for verification

## Annual Leave

Employees receive 20 days of annual leave per calendar year.



## Fabricated citation check

- Input: `This claim is cited as [999].`
- Accepted: **False**
- Validation result: Unknown citation [999] was used.
