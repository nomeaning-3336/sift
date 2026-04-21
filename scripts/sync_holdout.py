#!/usr/bin/env python3
"""Sync holdout and labels - add to holdout, remove overlaps from labels."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS_PATH = ROOT / "datasets" / "labeled" / "labels.csv"
HOLDOUT_PATH = ROOT / "datasets" / "labeled" / "holdout_adversarial.csv"

# Load existing labels
labels_rows = []
labels_texts = set()
with LABELS_PATH.open("r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) >= 2:
            text = ",".join(row[:-1])
            labels_texts.add(text)
            labels_rows.append((text, row[-1]))

# Load existing holdout
holdout_texts = set()
with HOLDOUT_PATH.open("r", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) >= 2:
            text = ",".join(row[:-1])
            holdout_texts.add(text)

print(f"Before: labels={len(labels_rows)}, holdout={len(holdout_texts)}")

# New entries to add to holdout (text, label_str)
new_entries = [
    # KEEPs
    ("GLIBC_2.3.4", "0"), ("GLIBC_2.2.5", "0"), ("GLIBC_2.38", "0"),
    ("LIBSELINUX_1.0", "0"), ("__IAT_end__", "0"), ("__imp___errno", "0"),
    ("__nm_program_invocation_short_name", "0"), ("_o__crt_atexit", "0"),
    ("_vsnwprintf", "0"), ("?what@exception@@UEBAPEBDXZ", "0"),
    (".CRT$XCZ", "0"), (".CRT$XPZ", "0"), (".CRT$XIZ", "0"), (".CRT$XIY", "0"),
    (".gfids", "0"), (".idata$3", "0"), (".idata$6", "0"),
    (".rdata$zzzdbg", "0"), (".rsrc$01", "0"), (".rsrc$02", "0"),
    (".text$x", "0"), (".note.gnu.property", "0"), (".note.gnu.build-id", "0"),
    (".eh_frame_hdr", "0"), (".gnu.version_r", "0"),
    ("RSDS", "0"), ("RSDSw", "0"),
    ("ia5String", "0"), ("ISO-8859-3", "0"),
    ("CP28591", "0"), ("CP28599", "0"), ("UTF-8", "0"),
    ("api-ms-win-core-profile-l1-1-0.dll", "0"),
    ("api-ms-win-core-processenvironment-l1-1-0.dll", "0"),
    ("api-ms-win-core-com-l1-1-0.dll", "0"), ("ADVAPI32.dll", "0"),
    ("libc.so.6", "0"),
    (r"onecore\internal\sdk\inc\wil\Staging.h", "0"),
    ("appidtel.pdb", "0"), ("TRUSTED CERTIFICATE", "0"),
    ("CKM_SHA_1_HMAC", "0"), ("CKM_SHA512_T_KEY_DERIVATION", "0"),
    ("CKM_SEED_CBC_ENCRYPT_DATA", "0"), ("CKK_EC_EDWARDS", "0"),
    ("CKA_IBM_NEVER_MODIFIABLE", "0"), ("CKA_TRUST_TIME_STAMPING", "0"),
    ("CKA_X2RATCHET_PNS", "0"), ("CKR_KEY_CHANGED", "0"),
    ("sha512-hmac", "0"), ("sha512-t-hmac", "0"), ("sha3-256-rsa-pkcs", "0"),
    ("sha3-512-rsa-pkcs", "0"), ("ssl3-md5-mac", "0"),
    ("wtls-client-key-and-mac-derive", "0"), ("x2ratchet-hks", "0"),
    ("skipjack-ecb64", "0"), ("baton-ecb96", "0"), ("rc2-key-gen", "0"),
    ("p11_extract_x509_directory", "0"), ("p11_save_open_file_in", "0"),
    ("assuan_begin_confidential", "0"),
    ("Perl_newXS", "0"), ("__imp_perl_destruct", "0"), ("__imp_GetACP", "0"),
    ("__imp_GetModuleHandleA", "0"), ("__imp_error", "0"), ("__imp_recv", "0"),
    ("__imp_memset", "0"), ("__imp_strstr", "0"), ("__imp_unlinkat", "0"),
    ("__imp_getpwnam", "0"),
    ("mbrtowc", "0"), ("memcmp", "0"), ("memset", "0"), ("malloc", "0"),
    ("calloc", "0"), ("fprintf", "0"), ("fcntl", "0"), ("getopt_long", "0"),
    ("gpg_strerror", "0"), ("strerror", "0"), ("wcslen", "0"),
    ("utf8_to_uchar", "0"), ("wcwidth", "0"),
    ("mftk.", "0"), ("tfD86t]", "0"), ("cdeZgii", "0"), ("Genu", "0"),
    ("NametKI", "0"), ("BootPerf", "0"), ("BootId", "0"), ("CountryName", "0"),
    ("ContainerId", "0"), ("FeatureVariantUsage", "0"),
    ("StartTimeTravelDebugging", "0"), ("DeleteScenarioInfo", "0"),
    ("FallbackError", "0"), ("CanAddMsaToMsTelemetry = (1 << 5)", "0"),
    ("KeepFirst = 0", "0"), ("KeepLast = 2", "0"), ("NotSet = 0,", "0"),
    ("Rundown = 0x80000", "0"), ("state->magic == 9827862", "0"),
    ("Version", "0"), ("version", "0"), ("escape", "0"), ("seed", "0"),
    ("False", "0"), ("Medium", "0"), ("fifo", "0"), ("LANG", "0"),
    ("TODAY", "0"), ("MONDAY", "0"), ("JUNE", "0"), ("FEBRUARY", "0"),
    ("%H:%M:%S", "0"), ("%Y-%m-%d", "0"), ("%2.2x ", "0"), ("%8.8x ", "0"),
    ("(Y-M-D) %s-%02d-%02d", "0"),
    (r'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "0"),
    (r'<application xmlns="urn:schemas-microsoft-com:asm.v3">', "0"),
    (r'  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">', "0"),
    ("      <requestedPrivileges>", "0"), ("        <assemblyIdentity", "0"),
    ("    </security>", "0"), ('    type="win32"/>', "0"),
    ("        <requestedExecutionLevel level=\"asInvoker\"/>", "0"),
    ("      <!--The ID below indicated application support for Windows 8 -->", "0"),
    ('<button foreground="graytext"/>', "0"),
    (r'<WMPDMCPlaylistButton background="themeable(dtb(EXPLORER::LISTVIEW, 1, 6), Highlight)"/>', "0"),
    ("<!-- Copyright (c) Microsoft Corporation -->", "0"),
    ("https://www.gnu.org/software/coreutils/", "0"),
    ("This is free software: you are free to change and redistribute it.", "0"),
    ("and --preserve-root=all is in effect", "0"),
    ("Multi-call invocation", "0"), ("David MacKenzie", "0"),
    ("Warning: using insecure memory!", "0"), ("incorrect timezone", "0"),
    ("network_down", "0"), ("address_family_not_supported", "0"),
    ("no certificate found", "0"), ("out of core", "0"),
    ("invalid string position", "0"), ("multiple output formats specified", "0"),
    ("string too long", "0"), ("Failed", "0"),
    ("message_size", "0"), ("attached_attrs", "0"),
    ("shell-escape-always", "0"), ("default-capshint", "0"),
    ("default-tt-hide", "0"), ("allow-emacs-prompt", "0"), ("pinentry-", "0"),
    ("no message available", "0"), ("no lock available", "0"),
    ("FileVer", "0"), ("GatherLogs", "0"), ("Sleep", "0"), ("SetWindowPos", "0"),
    ("LeaveCriticalSection", "0"), ("InitializeConditionVariable", "0"),
    ("DeleteCriticalSection", "0"), ("RegisterWindowMessageW", "0"),
    ("TranslateMessage", "0"), ("LoadLibraryExW", "0"),
    ("CreateSemaphoreW", "0"), ("BcdOpenSystemStore", "0"),
    ("GetSystemTimeAsFileTime", "0"), ("GetCurrentThreadId", "0"),
    ("UnRegisterTypeLib", "0"), ("CoTaskMemRealloc", "0"),
    ("RtlLookupFunctionEntry", "0"), ("RtlVirtualUnwind", "0"),
    ("TerminateProcess", "0"), ("EventWriteTransfer", "0"),
    ("EventSetInformation", "0"), ("EtwTrigger", "0"),
    ("SetupDiOpenDeviceInterfaceW", "0"),
    ("SetupDiDestroyDeviceInfoList", "0"), ("ShowWindow", "0"),
    ("RSDSw", "0"), ("RSDS", "0"), ("__IAT_end__", "0"),
    ("FIFTH", "0"), ("SIXTH", "0"),
    # JUNKs
    ("D$@H", "1"), ("D$8H", "1"), ("D$8I", "1"), ("D$8L", "1"),
    ("D$0I9", "1"), ("D$0L!|$0H", "1"), ("D$HJ", "1"), ("D$XL", "1"),
    ("D$XM", "1"), ("D$XH", "1"), ("D$HE3", "1"), ("D$HL", "1"),
    ("D$hH", "1"), ("D$hL", "1"), ("D$`A", "1"), ("D$`L", "1"),
    ("D$` ", "1"), ("D$PI", "1"), ("D$pD", "1"), ("D$pM", "1"),
    ("D$PM", "1"), ("D$TA", "1"), ("D$(A", "1"), ("D$(I", "1"),
    ("D$(E3", "1"), ("D$(I9G", "1"), ("D$^H)", "1"), ("D$0H;", "1"),
    ("D$@1", "1"),
    ("T$PH", "1"), ("T$PD", "1"), ("T$TH", "1"), ("T$XL", "1"),
    ("T$XH", "1"), ("T$WH", "1"), ("T$HH", "1"), ("T$PI", "1"),
    ("T$pM", "1"), ("T$0I", "1"), ("T$0E9", "1"), ("T$@E", "1"),
    ("T$ L", "1"), ("T$ M", "1"), ("T$`L", "1"),
    ("t$8H", "1"), ("t$XH", "1"), ("t$WH", "1"), ("t$ H", "1"),
    ("t$ M", "1"), ("t#D9\tt", "1"), ("t_q1J", "1"), ("tEA+", "1"),
    ("txL9", "1"), ("t9eH", "1"), ("t=eH", "1"),
    ("l$@H", "1"), ("l$PL", "1"), ("l$PH", "1"), ("l$PA", "1"),
    ("l$`H", "1"), ("l$hH", "1"), ("l$hI", "1"), ("l$ H", "1"),
    ("l$tE3", "1"), ("l$(H", "1"),
    ("L$@H", "1"), ("L$@L", "1"), ("L$PA", "1"), ("L$PH", "1"),
    ("L$PL", "1"), ("L$HL", "1"), ("L$XM", "1"), ("L$XH", "1"),
    ("L$`H", "1"), ("L$hH", "1"), ("L$hI", "1"), ("L$tD", "1"),
    ("L$ M", "1"), ("L$ 3", "1"), ("L#M@I", "1"),
    ("|$0A", "1"), ("|$0L", "1"), ("|$8H", "1"), ("|$@H", "1"),
    ("|$PH", "1"), ("|$pI", "1"), ("|$X1", "1"), ("|$XH", "1"),
    ("|$LA", "1"), ("|$ POSIt", "1"),
    (r"\$8H", "1"), (r"\$8I", "1"), (r"\$PI", "1"), (r"\$P3", "1"),
    (r"\$HH", "1"), (r"\$0H", "1"), (r"\$(@", "1"), (r"\$\D", "1"),
    (r"\$ UVWH", "1"), (r"\$ UVWAVAWH", "1"),
    ("@SVWH", "1"), ("@SUVWAVH", "1"), ("@USVWH", "1"),
    ("UVWH", "1"), ("UWAVH", "1"), ("UAVAWH", "1"), ("UATAUAVAWH", "1"),
    ("AVWVSH", "1"), ("AVAUATWVSH", "1"), ("AUATUWVSH", "1"),
    ("A_A^A\\", "1"), ("A_A^_", "1"), ("A_A^A]A\\_", "1"),
    ("A_A^A\\_^[]", "1"), ("0A^A]_", "1"), (" [^_]A\\", "1"),
    ("[^_]A\\A^A_", "1"), ("([^_]A\\A]", "1"), ("P[^_]A\\A]A^", "1"),
    ("8[^_]A\\A]", "1"), ("h[^_]A\\A]A^A_", "1"),
    ("XA_A^A]A\\_^][", "1"),
    ("spwwwwsssss0UUUUUUUUU77770wwwws77770UUUUUUUUU7ssspw", "1"),
    ("dddddddddddddddddddddddddddd", "1"), ("33333", "1"), ("3330", "1"),
    ("33333333333333333333333333333332", "1"),
    ("333333333333333333333333333333331", "1"),
    ("333333333333333332", "1"), ("#3332", "1"),
    ("TUUUUUUU1", "1"), ("UUUUUU", "1"), ("FFFfc", "1"),
    ("G+;'", "1"), ("K376Z", "1"), ("YFJ4", "1"), ("OGPS", "1"),
    ("NZST", "1"), ("SAST", "1"), ("CLST", "1"), ("VJ=2", "1"),
    ("BQG;", "1"), ("GE2t:", "1"), ("-LM<X", "1"), ("~ggg", "1"),
    ("~)I9~0", "1"), ("tm=}", "1"), ("w-H=", "1"),
    ("wtf", "0"),  # note: wtf is KEEP
    ("4`{{", "1"), ("4=pu", "1"), ("x*fA", "1"), ('0d)%"', "1"),
    ("&)h6", "1"), ("<Vw9H", "1"), ("A!@@", "1"),
]

# Partition into overlaps and new-only
overlap_texts = {t for t, l in new_entries if t in labels_texts}
new_only = [(t, l) for t, l in new_entries if t not in labels_texts]
new_only_holdout = [(t, l) for t, l in new_only if t not in holdout_texts]

print(f"Entries in new batch: {len(new_entries)}")
print(f"Overlaps with labels (will remove from labels): {len(overlap_texts)}")
print(f"New to add to holdout (not already there): {len(new_only_holdout)}")

# Remove overlaps from labels
removed = 0
with LABELS_PATH.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["line", "label"])
    for text, lbl in labels_rows:
        if text not in overlap_texts:
            w.writerow([text, lbl])
        else:
            removed += 1
print(f"Removed {removed} overlapping entries from labels.csv")

# Append new-only to holdout
with HOLDOUT_PATH.open("a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for text, lbl in new_only_holdout:
        w.writerow([text, lbl])
print(f"Added {len(new_only_holdout)} to {HOLDOUT_PATH.name}")

# Verify
with HOLDOUT_PATH.open("r", encoding="utf-8") as f:
    n_holdout = sum(1 for _ in f) - 1
with LABELS_PATH.open("r", encoding="utf-8") as f:
    n_labels = sum(1 for _ in f) - 1
print(f"After: labels={n_labels}, holdout={n_holdout}")
