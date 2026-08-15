import glob
import os
import re

base_dir = '/Users/nguyenquocnam/Desktop/hập tọc/KLTN/BrainTumor_WebApp/frontend'

def get_layout(role):
    # Sidebar links depend on role. We can just determine by file or generate a generic sidebar that shows links.
    # We will use JS in common.js to hide sidebar links based on role later, or we can just render all.
    pass

html_wrapper_top = """
<!-- Navigation and Sidebar inserted by update_ui.py -->
<nav class="fixed top-0 w-full z-50 bg-slate-50/80 backdrop-blur-xl shadow-sm border-none">
    <div class="flex justify-between items-center px-6 py-3 w-full max-w-screen-2xl mx-auto">
        <div class="flex items-center gap-8">
            <span class="text-xl font-bold tracking-tighter text-blue-800 font-headline">brainAI Studio</span>
            <div class="hidden md:flex gap-6 items-center">
            </div>
        </div>
        <div class="flex items-center gap-4">
            <p id="topUserName" class="text-sm font-semibold text-slate-700"></p>
            <p id="topUserRole" class="text-xs text-slate-500 hidden"></p>
            <button id="logoutBtn" class="px-3 py-1.5 bg-red-500 text-white rounded-lg text-xs font-bold hover:bg-red-600 transition shadow">Logout</button>
        </div>
    </div>
</nav>

<div class="flex pt-16 min-h-screen">
    <!-- SideNavBar -->
    <aside class="hidden lg:flex flex-col h-[calc(100vh-64px)] w-64 bg-slate-50 p-4 gap-2 border-r-0 fixed left-0">
        <div class="flex items-center gap-3 px-3 py-4 mb-4">
            <div class="w-10 h-10 bg-primary-container rounded-xl flex items-center justify-center text-on-primary">
                <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">psychology</span>
            </div>
            <div>
                <h2 class="text-blue-700 font-extrabold text-lg leading-tight">brainAI</h2>
                <p class="text-xs text-slate-500 uppercase tracking-widest font-semibold">Clinical Portal</p>
            </div>
        </div>
        <nav class="flex-1 flex flex-col gap-1 sidebar-nav-links">
            <a class="nav-btn flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-100 hover:translate-x-1 transition-all rounded-lg font-['Inter'] text-sm font-medium" href="doctor-dashboard.html" data-page="doctor-dashboard">
                <span class="material-symbols-outlined" data-icon="dashboard">dashboard</span> Dashboard (Dr)
            </a>
            <a class="nav-btn flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-100 hover:translate-x-1 transition-all rounded-lg font-['Inter'] text-sm font-medium" href="patient.html" data-page="patient">
                <span class="material-symbols-outlined" data-icon="dashboard">dashboard</span> Dashboard (Pt)
            </a>
            <a class="nav-btn flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-100 hover:translate-x-1 transition-all rounded-lg font-['Inter'] text-sm font-medium" href="analysis.html" data-page="analysis">
                <span class="material-symbols-outlined" data-icon="troubleshoot">troubleshoot</span> Analysis
            </a>
            <a class="nav-btn flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-100 hover:translate-x-1 transition-all rounded-lg font-['Inter'] text-sm font-medium" href="history.html" data-page="history">
                <span class="material-symbols-outlined" data-icon="folder_shared">history</span> Records
            </a>
            <a class="nav-btn flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-100 hover:translate-x-1 transition-all rounded-lg font-['Inter'] text-sm font-medium" href="appointments.html" data-page="appointments">
                <span class="material-symbols-outlined" data-icon="event">event</span> Appointments
            </a>
            <a class="nav-btn flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-100 hover:translate-x-1 transition-all rounded-lg font-['Inter'] text-sm font-medium" href="profiles.html" data-page="profiles">
                <span class="material-symbols-outlined" data-icon="group">group</span> Profiles
            </a>
            <a class="nav-btn flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-100 hover:translate-x-1 transition-all rounded-lg font-['Inter'] text-sm font-medium" href="messages.html" data-page="messages">
                <span class="material-symbols-outlined" data-icon="chat">chat</span> Messages
            </a>
        </nav>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 lg:ml-64 p-8 bg-surface">
        <div class="max-w-6xl mx-auto space-y-8">
"""

html_wrapper_bottom = """
        </div>
    </main>
</div>
<!-- Mobile Navigation -->
<div class="md:hidden fixed bottom-0 left-0 w-full bg-slate-50 border-t border-slate-200 z-50 px-6 py-2 flex justify-between items-center hide-patient">
    <button onclick="window.location.href='doctor-dashboard.html'" class="flex flex-col items-center gap-1 p-2 text-slate-500">
        <span class="material-symbols-outlined">dashboard</span>
        <span class="text-[10px] font-bold">Home</span>
    </button>
    <div class="relative -top-6">
        <button onclick="window.location.href='analysis.html'" class="w-14 h-14 bg-primary text-white rounded-full shadow-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-3xl">add</span>
        </button>
    </div>
    <button onclick="window.location.href='history.html'" class="flex flex-col items-center gap-1 p-2 text-slate-500">
        <span class="material-symbols-outlined">folder_shared</span>
        <span class="text-[10px] font-bold">Records</span>
    </button>
</div>
"""

# HTML head additions
head_additions = """
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <script id="tailwind-config">
          tailwind.config = { darkMode: "class", theme: { extend: { colors: { "on-primary-container": "#c8daff", "surface-variant": "#e1e3e4", "surface-container-lowest": "#ffffff", "on-surface-variant": "#424752", "on-primary": "#ffffff", "on-primary-fixed": "#001b3d", "surface-container-highest": "#e1e3e4", "on-tertiary-fixed-variant": "#793100", "secondary": "#4a5f83", "background": "#f8f9fa", "on-secondary-container": "#475c80", "tertiary-fixed": "#ffdbcb", "secondary-fixed-dim": "#b2c7f0", "primary-fixed-dim": "#a9c7ff", "surface-container-high": "#e7e8e9", "on-error": "#ffffff", "primary": "#00478d", "on-background": "#191c1d", "outline-variant": "#c2c6d4", "tertiary-container": "#9f4300", "surface-tint": "#005db6", "on-secondary-fixed-variant": "#32476a", "on-tertiary-container": "#ffcfb9", "primary-fixed": "#d6e3ff", "tertiary": "#793100", "surface": "#f8f9fa", "on-error-container": "#93000a", "surface-bright": "#f8f9fa", "outline": "#727783", "secondary-container": "#c0d5ff", "surface-dim": "#d9dadb", "error-container": "#ffdad6", "inverse-primary": "#a9c7ff", "tertiary-fixed-dim": "#ffb691", "on-secondary": "#ffffff", "surface-container": "#edeeef", "inverse-on-surface": "#f0f1f2", "primary-container": "#005eb8", "error": "#ba1a1a", "surface-container-low": "#f3f4f5", "on-secondary-fixed": "#021b3c", "on-tertiary": "#ffffff", "on-surface": "#191c1d", "on-primary-fixed-variant": "#00468c", "inverse-surface": "#2e3132", "on-tertiary-fixed": "#341100", "secondary-fixed": "#d6e3ff" }, fontFamily: { "headline": ["Manrope"], "body": ["Inter"], "label": ["Inter"] }, borderRadius: {"DEFAULT": "0.125rem", "lg": "0.25rem", "xl": "0.5rem", "full": "0.75rem"}, }, }, }
    </script>
    <style>
        .material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; display: inline-block; vertical-align: middle; }
    </style>
"""

# Pages that need rewriting
pages_to_rewrite = ['history.html', 'messages.html', 'doctor-dashboard.html', 'analysis.html', 'profiles.html']

for page in pages_to_rewrite:
    path = os.path.join(base_dir, page)
    if not os.path.exists(path): continue
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Update <head>
    if 'Manrope' not in content:
        content = content.replace('</head>', head_additions + '\n</head>')
    
    # 2. Extract <main> content
    main_match = re.search(r'<main[^>]*>([\s\S]*?)</main>', content)
    if not main_match: continue
    
    inner_main = main_match.group(1)
    
    # Remove old header
    content = re.sub(r'<header[^>]*>[\s\S]*?</header>', '', content)
    
    # Replace body contents (ignoring scripts at bottom)
    # We will just replace from <body...> to end of <main> with our new layout + inner_main
    body_start_match = re.search(r'<body[^>]*>', content)
    script_start = content.find('<script', main_match.end())
    if script_start == -1: script_start = content.find('</body>')
    
    scripts = content[script_start:]
    
    new_html = content[:body_start_match.end()] + '\n' + html_wrapper_top + inner_main + html_wrapper_bottom + '\n' + scripts
    
    # Ensure body tags have class
    new_html = re.sub(r'<body[^>]*>', '<body class="bg-surface font-body text-on-surface">', new_html)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f"Updated {page}")

print("Done updating HTML shells.")
