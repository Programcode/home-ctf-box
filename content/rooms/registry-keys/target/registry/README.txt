This tree simulates the Windows registry for training.

Real Windows stores these settings in binary hive files under
C:\Windows\System32\config (HKLM) and each profile's NTUSER.DAT
(HKCU). This lab cannot run Windows, so each key is a plain-text
.hiv file whose name matches the deepest key it represents and whose
header line records the full key path. Value names and their meaning
are faithful to Windows; the file format itself is a labeled
stand-in, not the real binary format.
