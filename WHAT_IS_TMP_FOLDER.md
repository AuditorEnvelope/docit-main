# 📁 **WHAT IS /tmp FOLDER? - COMPLETE EXPLANATION**

## **SIMPLE ANSWER**

```
/tmp = Operating System का Temporary Folder
```

---

## **WHERE IS IT?**

```
Mac/Linux: /tmp/
Windows: C:\Users\<username>\AppData\Local\Temp\
```

**On your Mac:**
```
/tmp/
```

---

## **WHAT IS IT USED FOR?**

```
/tmp folder = Temporary storage for applications
```

**Examples:**
- Browser downloads (temporary)
- Zip file extraction (temporary)
- Video encoding (temporary files)
- **Our system: Cloned repos (temporary)**

---

## **HOW OUR SYSTEM USES /tmp**

```
When Event Consumer processes an event:

1. Creates folder: /tmp/docai_smart_abc123xyz/
   ├─ This is a TEMPORARY folder
   └─ Created by Python's tempfile.mkdtemp()

2. Clones repo into it:
   └─ /tmp/docai_smart_abc123xyz/
      ├─ .git/ (git metadata)
      ├─ README.md
      ├─ src/
      ├─ docs/
      └─ ... (all repo files)

3. Generates documentation:
   └─ /tmp/docai_smart_abc123xyz/docs/
      ├─ SUMMARY.md
      ├─ ARCHITECTURE.md
      ├─ CHANGELOG.md
      └─ ... (generated docs)

4. Commits and pushes to GitHub

5. Deletes the entire folder:
   └─ /tmp/docai_smart_abc123xyz/ ❌ DELETED!
```

---

## **WHY USE /tmp?**

### **Reason 1: Temporary Storage**
```
We only need the repo during processing
After that, we don't need it anymore
So we delete it
```

### **Reason 2: Fast Access**
```
/tmp is usually on fast storage (RAM disk or SSD)
Faster than storing in permanent locations
```

### **Reason 3: Automatic Cleanup**
```
Operating system automatically cleans /tmp periodically
Old files get deleted automatically
No manual cleanup needed
```

### **Reason 4: No Disk Space Waste**
```
If we stored repos permanently:
- 1000 orgs × 100 MB per repo = 100 GB!
- Disk space would fill up quickly

Using /tmp:
- Only stores during processing
- Deletes immediately after
- Saves disk space
```

---

## **LIFECYCLE OF /tmp FOLDER**

```
┌─────────────────────────────────────────────────────────┐
│                  LIFECYCLE                              │
└─────────────────────────────────────────────────────────┘

1. EVENT RECEIVED
   └─ Event stored in PostgreSQL

2. EVENT CONSUMER STARTS PROCESSING
   └─ tmpdir = tempfile.mkdtemp(prefix="docai_smart_")
   └─ Creates: /tmp/docai_smart_abc123xyz/

3. CLONE REPO
   └─ git clone https://... /tmp/docai_smart_abc123xyz/
   └─ Repo files now in /tmp

4. GENERATE DOCS
   └─ Creates: /tmp/docai_smart_abc123xyz/docs/
   └─ Generates: SUMMARY.md, ARCHITECTURE.md, etc.

5. PUSH TO GITHUB
   └─ git push (using token)
   └─ Docs now in GitHub

6. CLEANUP
   └─ shutil.rmtree(tmpdir)
   └─ /tmp/docai_smart_abc123xyz/ ❌ DELETED!

7. UPDATE DATABASE
   └─ UPDATE commit_events SET processed = TRUE
   └─ Event marked as done

TOTAL LIFETIME: ~30 seconds to 2 minutes
```

---

## **WHAT HAPPENS TO /tmp?**

### **During Processing (While Event Consumer is Running)**
```
/tmp/docai_smart_abc123xyz/  ← EXISTS
├─ .git/
├─ src/
├─ docs/
│  ├─ SUMMARY.md
│  ├─ ARCHITECTURE.md
│  └─ CHANGELOG.md
└─ ... (all files)

Size: ~50-200 MB (depends on repo size)
Lifetime: ~30 seconds to 2 minutes
```

### **After Processing (After Event Consumer Finishes)**
```
/tmp/docai_smart_abc123xyz/  ← DELETED!

Nothing left in /tmp from our system
```

---

## **HOW TO SEE /tmp FOLDER**

### **On Mac Terminal:**
```bash
# See all temp folders
ls -la /tmp/

# See only our temp folders
ls -la /tmp/ | grep docai_smart

# See size of temp folder
du -sh /tmp/docai_smart_*

# Watch in real-time (while event consumer is running)
watch -n 1 'ls -la /tmp/ | grep docai_smart'
```

### **Example Output (While Processing):**
```
drwx------  5 harshsrivastava  wheel  160 Oct 26 00:45 docai_smart_abc123xyz
drwx------  5 harshsrivastava  wheel  160 Oct 26 00:46 docai_smart_def456uvw
drwx------  5 harshsrivastava  wheel  160 Oct 26 00:47 docai_smart_ghi789rst
```

### **Example Output (After Processing):**
```
(no docai_smart folders - all deleted!)
```

---

## **CODE THAT CREATES AND DELETES /tmp**

### **Create /tmp Folder:**
```python
# File: src/processors/smart_processor.py (Line 95)
tmpdir = tempfile.mkdtemp(prefix="docai_smart_")
# Creates: /tmp/docai_smart_abc123xyz/
```

### **Delete /tmp Folder:**
```python
# File: src/processors/smart_processor.py (Line 145)
finally:
    shutil.rmtree(tmpdir)
# Deletes: /tmp/docai_smart_abc123xyz/
```

---

## **IMPORTANT POINTS**

### **✅ What's Correct:**
```
✅ /tmp is temporary
✅ /tmp is cleaned up automatically
✅ /tmp doesn't use permanent disk space
✅ /tmp is fast
✅ /tmp is safe (isolated per process)
```

### **❌ What's NOT Correct:**
```
❌ /tmp is NOT permanent storage
❌ /tmp is NOT for keeping files
❌ /tmp is NOT backed up
❌ /tmp is NOT for important data
```

---

## **COMPARISON: /tmp vs PostgreSQL**

| Aspect | /tmp | PostgreSQL |
|--------|------|-----------|
| **Purpose** | Temporary workspace | Permanent storage |
| **Lifetime** | During processing | Forever |
| **Deleted?** | ✅ YES (automatically) | ❌ NO (persisted) |
| **Survives restart?** | ❌ NO | ✅ YES |
| **Survives power loss?** | ❌ NO | ✅ YES |
| **Use case** | Working directory | Data storage |

---

## **REAL EXAMPLE**

### **Scenario: Processing 1 Event**

```
Time: 00:00:00
├─ Event received from GitHub
├─ Stored in PostgreSQL
└─ Event Consumer starts processing

Time: 00:00:05
├─ /tmp/docai_smart_abc123xyz/ CREATED
├─ Repo cloned (50 MB)
└─ Size: 50 MB

Time: 00:00:10
├─ Docs generated
├─ /tmp/docai_smart_abc123xyz/docs/ created
└─ Size: 52 MB

Time: 00:00:15
├─ Docs pushed to GitHub
├─ /tmp/docai_smart_abc123xyz/ DELETED
└─ Size: 0 MB

Time: 00:00:20
├─ Database updated (processed=TRUE)
└─ Event complete!

TOTAL DISK USAGE: 52 MB for 15 seconds
FINAL DISK USAGE: 0 MB (deleted)
```

---

## **SUMMARY**

### **What is /tmp?**
```
Operating system's temporary folder
```

### **Where is it?**
```
/tmp/ (on Mac/Linux)
C:\Users\...\AppData\Local\Temp\ (on Windows)
```

### **What do we store there?**
```
Cloned repositories (during processing only)
```

### **How long does it stay?**
```
~30 seconds to 2 minutes (during processing)
Then automatically deleted
```

### **Why use /tmp?**
```
✅ Fast
✅ Temporary (no permanent storage)
✅ Automatic cleanup
✅ Saves disk space
```

### **Is it safe?**
```
✅ YES - Isolated per process
✅ YES - Automatically cleaned up
✅ YES - No data loss (data is in PostgreSQL)
```

---

## **BOTTOM LINE**

```
/tmp = Temporary working directory
       Used only during processing
       Automatically deleted after
       No permanent data stored there
       All important data in PostgreSQL
```

**Think of it like:** 
```
Temporary desk where you work on a document
After you're done, you clean the desk
The final document is saved in a file (PostgreSQL)
```

🎯 **Everything important is in PostgreSQL!**
