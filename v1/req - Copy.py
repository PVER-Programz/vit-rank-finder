import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
# Ranking - find rank for this student and show Top 10 leaderboard
RANK_TARGET = "24BVD1077" 

# Derived automatically from RANK_TARGET (Year + Branch)
PREFIX = RANK_TARGET[:5] 

START_NUM = 1000
END_NUM = 1130
MAX_WORKERS = 20

# API Endpoints
SEARCH_URL = "https://vit-grade.onrender.com/api/search?q="
GRADE_URL_TEMPLATE = "https://vit-grade.onrender.com/api/grades/{year}/{branch}/{regno}"

session = requests.Session()

def fetch_all_data(num):
    """Verifies existence and fetches CGPA in one efficient step."""
    regno = f"{PREFIX}{num}"
    try:
        # Step 1: Search API (Existence check)
        r = session.get(SEARCH_URL + regno, timeout=10)
        r.raise_for_status()
        search_results = r.json()
        
        for student in search_results:
            if student.get("regNo", "").upper() == regno:
                # Step 2: Grade API (Data extraction)
                year, branch = regno[:2], regno[2:5]
                grade_url = GRADE_URL_TEMPLATE.format(year=year, branch=branch, regno=regno)
                g_resp = session.get(grade_url, timeout=15)
                g_resp.raise_for_status()
                data = g_resp.json()
                
                name = data.get("student_information", {}).get("name", "Unknown")
                cgpa_list = data.get("tables", {}).get("cgpa_details", [])
                cgpa = cgpa_list[0].get("Cgpa", "N/A") if cgpa_list else "N/A"
                
                return {"regno": regno, "name": name, "cgpa": cgpa}
    except Exception:
        pass
    return None

def main():
    print(f"\n🚀 Processing Batch: {PREFIX} (Range: {START_NUM}-{END_NUM})")
    print("-" * 65)
    
    start_time = time.perf_counter()
    found_students = []
    total_count = END_NUM - START_NUM + 1
    processed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_all_data, n): n for n in range(START_NUM, END_NUM + 1)}
        
        for future in as_completed(futures):
            res, num = future.result(), futures[future]
            processed += 1
            if res:
                found_students.append(res)
            
            # Progress Dashboard
            elapsed = time.perf_counter() - start_time
            avg = elapsed / processed
            rem = avg * (total_count - processed)
            prog = (processed / total_count) * 100
            
            if res:
                # Extra Highlight if it's our target
                is_target = " ⭐" if res['regno'].upper() == RANK_TARGET.upper() else ""
                status = f"FOUND {res['regno']}" + (f" | {res['cgpa']}" if res['cgpa'] != 'N/A' else "") + is_target
            else:
                status = f"Checking {PREFIX}{num}"
            
            print(f"{prog:6.2f}% | {status:<35} | ETA {rem:5.2f}s")

    # --- GENERATING REPORTS ---
    found_students.sort(key=lambda x: x['regno'])
    found_regnos = [s['regno'] for s in found_students]
    
    # Discovery Report
    reg_file = f"regnos_{PREFIX}_{START_NUM}_{END_NUM}.json"
    expected = {f"{PREFIX}{n}" for n in range(START_NUM, END_NUM + 1)}
    missing = sorted(expected - set(found_regnos))
    discovery_data = {
        "prefix": PREFIX, "range": [START_NUM, END_NUM],
        "total_found": len(found_students), "missing_count": len(missing),
        "found_regnos": found_regnos, "missing_regnos": missing
    }
    with open(reg_file, "w", encoding='utf-8') as f:
        json.dump(discovery_data, f, indent=4)

    # Intelligence Report
    cgpa_file = f"Cgpa_{PREFIX}.json"
    with open(cgpa_file, "w", encoding='utf-8') as f:
        json.dump(found_students, f, indent=4)

    print("-" * 65)
    print(f"✅ Generated Discovery Report: {reg_file}")
    print(f"✅ Generated CGPA Intelligence: {cgpa_file}")

    # --- RANKING & TOP 10 ---
    ranked = []
    for s in found_students:
        try:
            val = float(s.get('cgpa', 0))
            if val > 0: ranked.append(s)
        except (ValueError, TypeError): continue
    
    ranked.sort(key=lambda x: float(x['cgpa']), reverse=True)

    if RANK_TARGET:
        print("\n" + "🎓" + f" RANK REPORT: {RANK_TARGET} " + "🎓")
        found_t = False
        target_upper = RANK_TARGET.upper()
        for i, s in enumerate(ranked, 1):
            if s['regno'].upper() == target_upper:
                print(f"  - Student: {s['name']}")
                print(f"  - CGPA:    {s['cgpa']}")
                print(f"  - Rank:    #{i} (out of {len(ranked)} valid records)")
                found_t = True
                break
        if not found_t:
            print(f"  Student {RANK_TARGET} not found or no valid CGPA available.")

    # Top 10 Leaderboard
    print("\n" + "🏆" + " TOP 10 LEADERBOARD " + "🏆")
    print(f"{'Rank':<6} | {'Reg No':<10} | {'Name':<30} | {'CGPA':<5}")
    print("-" * 60)
    for i, s in enumerate(ranked[:10], 1):
        # Mark target in leaderboard if present
        star = "*" if s['regno'].upper() == RANK_TARGET.upper() else " "
        print(f"#{i:<5}{star}| {s['regno']:<10} | {s['name'][:30]:<30} | {s['cgpa']:<5}")
    
    print("-" * 60)
    print(f"\nALL TASKS COMPLETE in {time.perf_counter() - start_time:.2f}s")

if __name__ == "__main__":
    main()