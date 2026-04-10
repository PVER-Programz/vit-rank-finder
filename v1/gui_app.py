import tkinter as tk
import customtkinter as ctk
import requests
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION & GLOBAL STATE ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

found_students = []
scanning = False
session = requests.Session()
current_frame = "scanner"

# --- CORE LOGIC FUNCTIONS ---

def log(message):
    log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
    log_box.see("end")

def show_frame(name):
    global current_frame
    current_frame = name
    
    # Toggle display
    if name == "scanner":
        scanner_frame.grid(row=0, column=1, sticky="nsew")
        leaderboard_frame.grid_forget()
        scanner_btn.configure(fg_color=("gray75", "gray25"))
        leaderboard_btn.configure(fg_color="transparent")
    else:
        leaderboard_frame.grid(row=0, column=1, sticky="nsew")
        scanner_frame.grid_forget()
        leaderboard_btn.configure(fg_color=("gray75", "gray25"))
        scanner_btn.configure(fg_color="transparent")
        update_leaderboard_ui()

def update_leaderboard_ui():
    # Clear existing items
    for widget in results_scroll.winfo_children():
        widget.destroy()

    if not found_students:
        return

    # Sort logic
    ranked = []
    for s in found_students:
        try:
            val = float(s.get('cgpa', 0))
            if val > 0: ranked.append(s)
        except: continue
    
    ranked.sort(key=lambda x: float(x['cgpa']), reverse=True)
    target = target_entry.get().upper()

    # Update Rank Highlight Card
    found_t = False
    for i, s in enumerate(ranked, 1):
        if s['regno'].upper() == target:
            rank_info_label.configure(text=f"⭐ {s['name']} | CGPA: {s['cgpa']} | Rank: #{i} of {len(ranked)}", text_color="#f1c40f")
            found_t = True
            break
    if not found_t:
        rank_info_label.configure(text=f"Target {target} not found in current scan.", text_color="white")

    # Populate List
    for i, s in enumerate(ranked, 1):
        is_target = s['regno'].upper() == target
        row_color = "#1e3799" if is_target else "transparent"
        item = ctk.CTkFrame(results_scroll, height=45, fg_color=row_color)
        item.pack(fill="x", pady=2)
        
        ctk.CTkLabel(item, text=f"#{i}", width=60).pack(side="left", padx=10)
        ctk.CTkLabel(item, text=s['regno'], width=120).pack(side="left", padx=10)
        ctk.CTkLabel(item, text=s['name'][:35], width=300, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(item, text=s['cgpa'], width=80, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)

def start_scan():
    global scanning, found_students
    if scanning: return
    
    scanning = True
    found_students = []
    start_btn.configure(state="disabled", text="SCANNING...", fg_color="#e67e22")
    log_box.delete("1.0", "end")
    
    # Start in background thread
    threading.Thread(target=run_scanner_logic, daemon=True).start()

def run_scanner_logic():
    global scanning
    target = target_entry.get().upper()
    prefix = target[:5]
    start_num = int(start_entry.get())
    end_num = int(end_entry.get())
    max_workers = int(workers_entry.get())
    
    search_url = "https://vit-grade.onrender.com/api/search?q="
    grade_url_template = "https://vit-grade.onrender.com/api/grades/{year}/{branch}/{regno}"
    
    nums = list(range(start_num, end_num + 1))
    total = len(nums)
    processed = 0

    log(f"Starting Scan for {prefix} range {start_num}-{end_num}...")

    def fetch_data(num):
        regno = f"{prefix}{num}"
        try:
            r = session.get(search_url + regno, timeout=10)
            if r.status_code == 200:
                results = r.json()
                for student in results:
                    if student.get("regNo", "").upper() == regno:
                        y, b = regno[:2], regno[2:5]
                        g_resp = session.get(grade_url_template.format(year=y, branch=b, regno=regno), timeout=15)
                        data = g_resp.json()
                        name = data.get("student_information", {}).get("name", "Unknown")
                        cgpa_list = data.get("tables", {}).get("cgpa_details", [])
                        cgpa = cgpa_list[0].get("Cgpa", "N/A") if cgpa_list else "N/A"
                        return {"regno": regno, "name": name, "cgpa": cgpa}
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_data, n): n for n in nums}
        for future in as_completed(futures):
            res = future.result()
            processed += 1
            
            # Progress calculation
            progress = processed / total
            progress_bar.set(progress)
            pct = int(progress * 100)
            
            if res:
                found_students.append(res)
                status_label.configure(text=f"Progress: {pct}% | Found {res['regno']} ({res['cgpa']})")
                log(f"FOUND: {res['regno']} - {res['name']} (CGPA: {res['cgpa']})")
            else:
                status_label.configure(text=f"Progress: {pct}% | Checking {prefix}{futures[future]}...")

    scanning = False
    start_btn.configure(state="normal", text="START SCANNING", fg_color="#2ecc71")
    log(f"Scan Complete! Found {len(found_students)} students.")
    
    # Save results
    with open(f"Cgpa_{prefix}_Latest.json", "w") as f:
        json.dump(found_students, f, indent=4)
    
    # Switch to leaderboard automatically
    app.after(500, lambda: show_frame("leaderboard"))

# --- UI INITIALIZATION ---
app = ctk.CTk()
app.title("VIT Grade Intelligence Dashboard")
app.geometry("1100x700")
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=1)

# --- SIDEBAR ---
sidebar_frame = ctk.CTkFrame(app, width=200, corner_radius=0)
sidebar_frame.grid(row=0, column=0, sticky="nsew")
sidebar_frame.grid_rowconfigure(4, weight=1)

ctk.CTkLabel(sidebar_frame, text="VIT GRADE\nINTEL", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

scanner_btn = ctk.CTkButton(sidebar_frame, text="Scanner", command=lambda: show_frame("scanner"), anchor="w", height=40)
scanner_btn.grid(row=1, column=0, padx=20, pady=10)

leaderboard_btn = ctk.CTkButton(sidebar_frame, text="Leaderboard", command=lambda: show_frame("leaderboard"), anchor="w", height=40)
leaderboard_btn.grid(row=2, column=0, padx=20, pady=10)

ctk.CTkOptionMenu(sidebar_frame, values=["Dark", "Light"], command=ctk.set_appearance_mode).grid(row=6, column=0, padx=20, pady=(10, 20))

# --- SCANNER FRAME ---
scanner_frame = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")
scanner_frame.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(scanner_frame, text="Batch Intelligence Scanner", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")

config_panel = ctk.CTkFrame(scanner_frame)
config_panel.grid(row=1, column=0, padx=30, sticky="nsew")
config_panel.grid_columnconfigure((0, 1, 2, 3), weight=1)

# Input Helper
def create_entry(parent, label, default, col):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.grid(row=0, column=col, padx=10, pady=15, sticky="ew")
    ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=12)).pack(anchor="w")
    e = ctk.CTkEntry(f, width=150)
    e.insert(0, default)
    e.pack(pady=(5, 0))
    return e

target_entry = create_entry(config_panel, "Target Reg No:", "24BVD1077", 0)
start_entry = create_entry(config_panel, "Start Num:", "1000", 1)
end_entry = create_entry(config_panel, "End Num:", "1130", 2)
workers_entry = create_entry(config_panel, "Workers:", "20", 3)

start_btn = ctk.CTkButton(scanner_frame, text="START SCANNING", font=ctk.CTkFont(size=14, weight="bold"), height=45, fg_color="#2ecc71", hover_color="#27ae60", command=start_scan)
start_btn.grid(row=2, column=0, padx=30, pady=30, sticky="ew")

progress_bar = ctk.CTkProgressBar(scanner_frame)
progress_bar.grid(row=3, column=0, padx=30, pady=(0, 10), sticky="ew")
progress_bar.set(0)

status_label = ctk.CTkLabel(scanner_frame, text="Ready to scan...", font=ctk.CTkFont(size=13))
status_label.grid(row=4, column=0, padx=30, pady=0, sticky="w")

log_box = ctk.CTkTextbox(scanner_frame, height=250, font=ctk.CTkFont(family="Consolas", size=12))
log_box.grid(row=5, column=0, padx=30, pady=20, sticky="nsew")
scanner_frame.grid_rowconfigure(5, weight=1)

# --- LEADERBOARD FRAME ---
leaderboard_frame = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent")
leaderboard_frame.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(leaderboard_frame, text="🏆 Top Academic Performers", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

rank_card = ctk.CTkFrame(leaderboard_frame, height=80, fg_color="#34495e")
rank_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
rank_info_label = ctk.CTkLabel(rank_card, text="Scan to see your ranking...", font=ctk.CTkFont(size=16, weight="bold"))
rank_info_label.place(relx=0.5, rely=0.5, anchor="center")

table_header = ctk.CTkFrame(leaderboard_frame, height=40, fg_color="#2c3e50")
table_header.grid(row=2, column=0, padx=30, pady=(10, 0), sticky="ew")
ctk.CTkLabel(table_header, text="Rank", width=60, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
ctk.CTkLabel(table_header, text="Reg No", width=120, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
ctk.CTkLabel(table_header, text="Name", width=300, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
ctk.CTkLabel(table_header, text="CGPA", width=80, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)

results_scroll = ctk.CTkScrollableFrame(leaderboard_frame, fg_color="transparent")
results_scroll.grid(row=3, column=0, padx=30, pady=(0, 30), sticky="nsew")
leaderboard_frame.grid_rowconfigure(3, weight=1)

# --- START APP ---
show_frame("scanner")
app.mainloop()
