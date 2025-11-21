#!/usr/bin/env python3
"""
Reddit Poster GUI - User-friendly interface for the Reddit posting bot
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import asyncio
import threading
import os
from pathlib import Path
import json
import requests

from reddit_poster import RedditPoster, PostData

class RedditPosterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Reddit Poster Bot")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)  # Set minimum window size
        
        # Configure modern styling
        self.setup_styles()
        
        self.poster = RedditPoster()
        self.scheduler_running = False
        self.scheduler_thread = None
        self.current_username = None
        self.login_future = None
        self.account_thread = None
        
        # Track active context menus and tooltips for proper cleanup
        self.active_menus = []
        self.active_tooltips = []
        
        self.setup_ui()
        self.setup_global_bindings()
        self.refresh_accounts()
        self.refresh_posts()

    def setup_styles(self):
        """Setup modern styling for the application"""
        style = ttk.Style()
        
        # Configure modern theme
        try:
            # Try to use a modern theme if available
            available_themes = style.theme_names()
            if 'clam' in available_themes:
                style.theme_use('clam')
            elif 'alt' in available_themes:
                style.theme_use('alt')
        except:
            pass
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Heading.TLabel', font=('Segoe UI', 10, 'bold'))
        
        # Configure notebook tabs
        style.configure('TNotebook.Tab', padding=[20, 8])
        
        # Configure buttons
        style.configure('Action.TButton', font=('Segoe UI', 9, 'bold'))
        
    def setup_global_bindings(self):
        """Setup global event bindings for better UX"""
        # Hide context menus when clicking elsewhere (but not on treeviews)
        self.root.bind("<Button-1>", self.on_global_click)
        
        # Hide menus when switching tabs
        self.root.bind("<<NotebookTabChanged>>", self.hide_all_menus)
        
        # Hide menus and tooltips on key press
        self.root.bind("<Key>", lambda e: (self.hide_all_menus(), self.hide_all_tooltips()))
        
        # Add keyboard shortcuts
        self.root.bind("<Control-r>", lambda e: self.refresh_current_tab())
        self.root.bind("<F5>", lambda e: self.refresh_current_tab())
        self.root.bind("<Escape>", lambda e: (self.hide_all_menus(), self.hide_all_tooltips()))
        
    def on_global_click(self, event):
        """Handle global clicks to hide menus when appropriate"""
        # Check if the click is on a treeview widget
        widget = event.widget
        if not isinstance(widget, ttk.Treeview):
            self.hide_all_menus()
        # Always hide tooltips on any click
        self.hide_all_tooltips()
        
    def hide_all_menus(self, event=None):
        """Hide all active context menus"""
        for menu in self.active_menus:
            try:
                menu.unpost()
            except:
                pass
        self.active_menus.clear()
        
    def hide_all_tooltips(self):
        """Hide all active tooltips"""
        # Hide all tooltips using the new robust system
        if hasattr(self, 'active_tooltips'):
            # Make a copy of the list to avoid modification during iteration
            tooltips_to_hide = self.active_tooltips.copy()
            for tooltip in tooltips_to_hide:
                try:
                    tooltip.hide_tooltip()
                except:
                    pass
            self.active_tooltips.clear()
        
        # Also clean up any old-style tooltips that might still exist
        def hide_old_tooltips_recursive(widget):
            if hasattr(widget, 'tooltip'):
                try:
                    widget.tooltip.destroy()
                    del widget.tooltip
                except:
                    pass
            
            if hasattr(widget, '_tooltips'):
                for tooltip in widget._tooltips:
                    try:
                        tooltip.hide_tooltip()
                    except:
                        pass
            
            try:
                for child in widget.winfo_children():
                    hide_old_tooltips_recursive(child)
            except:
                pass
        
        hide_old_tooltips_recursive(self.root)
        
    def safe_hide_menu(self, menu):
        """Safely hide a specific menu"""
        try:
            menu.unpost()
            if menu in self.active_menus:
                self.active_menus.remove(menu)
        except:
            pass
            
    def refresh_current_tab(self):
        """Refresh the currently active tab"""
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text")
            if current_tab == "Accounts":
                self.refresh_accounts()
            elif current_tab == "Posts":
                self.refresh_posts()
            elif current_tab == "Proxies":
                self.refresh_proxies()
            elif current_tab == "Scheduler":
                self.update_scheduler_status()
        except:
            pass
            
    def on_tab_changed(self, event=None):
        """Handle notebook tab change"""
        self.hide_all_menus()
        self.hide_all_tooltips()  # Hide any visible tooltips when switching tabs
        
        # Refresh data when switching to certain tabs
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text")
            if current_tab == "Accounts":
                self.refresh_accounts()
            elif current_tab == "Posts":
                self.refresh_posts()
            elif current_tab == "Proxies":
                self.refresh_proxies()
        except:
            pass

    def setup_ui(self):
        """Setup the user interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Bind notebook tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Accounts tab
        self.setup_accounts_tab(self.notebook)
        
        # Posts tab
        self.setup_posts_tab(self.notebook)
        
        # Proxies tab
        self.setup_proxies_tab(self.notebook)
        
        # Scheduler tab
        self.setup_scheduler_tab(self.notebook)
        
        # Status bar
        self.setup_status_bar()

    def setup_accounts_tab(self, notebook):
        """Setup accounts management tab"""
        accounts_frame = ttk.Frame(notebook)
        notebook.add(accounts_frame, text="Accounts")
        
        # Add account section
        add_frame = ttk.LabelFrame(accounts_frame, text="Add New Account")
        add_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Row 0 - Username
        ttk.Label(add_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.username_entry = ttk.Entry(add_frame, width=30)
        self.username_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Row 1 - Proxy Selection
        ttk.Label(add_frame, text="Proxy:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.account_proxy_combo = ttk.Combobox(add_frame, width=40, state="readonly")
        self.account_proxy_combo.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W+tk.E)
        
        # Row 2 - Proxy Usage Options
        proxy_options_frame = ttk.Frame(add_frame)
        proxy_options_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W+tk.E)
        
        self.use_proxy_for_account_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(proxy_options_frame, text="Use proxy for this account", 
                       variable=self.use_proxy_for_account_var).pack(side=tk.LEFT, padx=5)
        
        # Row 3 - Add Button
        add_account_btn = ttk.Button(add_frame, text="Add Account", command=self.add_account, style="Action.TButton")
        add_account_btn.grid(row=3, column=0, columnspan=3, padx=5, pady=10)
        self.create_tooltip(add_account_btn, "Add a new Reddit account to the bot")
        
        # Login confirmation section (initially hidden)
        self.login_confirm_frame = ttk.Frame(add_frame)
        self.login_confirm_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W+tk.E)
        self.login_confirm_frame.grid_remove()  # Hide initially
        
        self.login_status_label = ttk.Label(self.login_confirm_frame, text="", foreground="blue")
        self.login_status_label.pack(side=tk.LEFT, padx=5)
        
        self.confirm_login_button = ttk.Button(self.login_confirm_frame, text="Confirm Login", 
                                             command=self.confirm_login, state=tk.DISABLED)
        self.confirm_login_button.pack(side=tk.RIGHT, padx=5)
        
        # Accounts list
        list_frame = ttk.LabelFrame(accounts_frame, text="Existing Accounts")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for accounts with better column sizing
        columns = ("Username", "Status", "Posts", "Proxy", "Last Used")
        self.accounts_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Configure columns with better proportions
        self.accounts_tree.heading("Username", text="Username")
        self.accounts_tree.column("Username", width=150, minwidth=100)
        
        self.accounts_tree.heading("Status", text="Status")
        self.accounts_tree.column("Status", width=80, minwidth=60)
        
        self.accounts_tree.heading("Posts", text="Posts")
        self.accounts_tree.column("Posts", width=60, minwidth=50)
        
        self.accounts_tree.heading("Proxy", text="Proxy")
        self.accounts_tree.column("Proxy", width=250, minwidth=150)
        
        self.accounts_tree.heading("Last Used", text="Last Used")
        self.accounts_tree.column("Last Used", width=150, minwidth=100)
        
        scrollbar_accounts = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.accounts_tree.yview)
        self.accounts_tree.configure(yscrollcommand=scrollbar_accounts.set)
        
        self.accounts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_accounts.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Manual account usage section
        manual_frame = ttk.LabelFrame(accounts_frame, text="Manual Account Usage")
        manual_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Account selection for manual use
        ttk.Label(manual_frame, text="Select Account:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.manual_account_combo = ttk.Combobox(manual_frame, width=30, state="readonly")
        self.manual_account_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Manual usage buttons
        button_frame = ttk.Frame(manual_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        load_account_btn = ttk.Button(button_frame, text="Load Account", command=self.load_account_manually, style="Action.TButton")
        load_account_btn.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(load_account_btn, "Load account with its proxy and cookies for manual use")
        
        self.update_cookies_btn = ttk.Button(button_frame, text="Update Cookies", command=self.update_account_cookies, state=tk.DISABLED)
        self.update_cookies_btn.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(self.update_cookies_btn, "Update account cookies from current browser session")
        
        self.close_session_btn = ttk.Button(button_frame, text="Close Session", command=self.close_manual_session, state=tk.DISABLED)
        self.close_session_btn.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(self.close_session_btn, "Close the current manual browser session")
        
        # Manual session status
        self.manual_session_status = ttk.Label(manual_frame, text="No active session", foreground="gray")
        self.manual_session_status.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Store manual session info
        self.manual_browser = None
        self.manual_page = None
        self.manual_playwright = None
        self.manual_loop = None
        self.manual_account_name = None
        
        manual_frame.columnconfigure(1, weight=1)

        # Context menu for accounts
        self.accounts_menu = tk.Menu(self.root, tearoff=0, font=('Segoe UI', 9))
        self.accounts_menu.add_command(label="Edit Proxy Settings", command=self.edit_account_proxy)
        self.accounts_menu.add_separator()
        self.accounts_menu.add_command(label="Remove Account", command=self.remove_account)
        self.accounts_tree.bind("<Button-3>", self.show_accounts_menu)
        self.accounts_tree.bind("<Button-1>", self.hide_all_menus)

    def setup_posts_tab(self, notebook):
        """Setup posts management tab"""
        posts_frame = ttk.Frame(notebook)
        notebook.add(posts_frame, text="Posts")
        
        # Add post section
        add_frame = ttk.LabelFrame(posts_frame, text="Add New Post")
        add_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Row 0
        ttk.Label(add_frame, text="Subreddit:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.subreddit_entry = ttk.Entry(add_frame, width=20)
        self.subreddit_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(add_frame, text="Account:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.account_combo = ttk.Combobox(add_frame, width=20, state="readonly")
        self.account_combo.grid(row=0, column=3, padx=5, pady=2)
        
        # Row 1
        ttk.Label(add_frame, text="Title:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.title_entry = ttk.Entry(add_frame, width=50)
        self.title_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=2, sticky=tk.W+tk.E)
        
        # Row 2
        ttk.Label(add_frame, text="Type:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.post_type_var = tk.StringVar(value="text")
        type_frame = ttk.Frame(add_frame)
        type_frame.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)
        
        ttk.Radiobutton(type_frame, text="Text", variable=self.post_type_var, value="text", 
                       command=self.on_post_type_change).pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="Image", variable=self.post_type_var, value="image",
                       command=self.on_post_type_change).pack(side=tk.LEFT, padx=(10, 0))
        
        self.nsfw_var = tk.BooleanVar()
        ttk.Checkbutton(add_frame, text="NSFW", variable=self.nsfw_var).grid(row=2, column=2, padx=5, pady=2, sticky=tk.W)
        
        # Row 3 - Content
        ttk.Label(add_frame, text="Content:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=2)
        
        self.content_frame = ttk.Frame(add_frame)
        self.content_frame.grid(row=3, column=1, columnspan=3, padx=5, pady=2, sticky=tk.W+tk.E)
        
        # Text content
        self.text_content = tk.Text(self.content_frame, height=4, width=60)
        self.text_content.pack(fill=tk.BOTH, expand=True)
        
        # Image content
        self.image_frame = ttk.Frame(self.content_frame)
        
        # Image list display
        self.image_list_frame = ttk.Frame(self.image_frame)
        self.image_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Listbox to show selected images
        self.image_listbox = tk.Listbox(self.image_list_frame, height=4, selectmode=tk.EXTENDED)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for image list
        image_scrollbar = ttk.Scrollbar(self.image_list_frame, orient=tk.VERTICAL, command=self.image_listbox.yview)
        self.image_listbox.configure(yscrollcommand=image_scrollbar.set)
        image_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Image control buttons
        self.image_buttons_frame = ttk.Frame(self.image_frame)
        self.image_buttons_frame.pack(fill=tk.X)
        
        ttk.Button(self.image_buttons_frame, text="Add Images", command=self.browse_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.image_buttons_frame, text="Remove Selected", command=self.remove_selected_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.image_buttons_frame, text="Clear All", command=self.clear_all_images).pack(side=tk.LEFT, padx=(0, 5))
        
        # Store image paths
        self.selected_image_paths = []
        
        # Row 4 - Browser Options
        ttk.Label(add_frame, text="Browser:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        
        browser_options_frame = ttk.Frame(add_frame)
        browser_options_frame.grid(row=4, column=1, columnspan=3, padx=5, pady=2, sticky=tk.W)
        
        self.use_proxy_for_post_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Use account's proxy", 
                       variable=self.use_proxy_for_post_var).pack(side=tk.LEFT)
        
        self.headless_for_post_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(browser_options_frame, text="Headless mode", 
                       variable=self.headless_for_post_var).pack(side=tk.LEFT, padx=(20, 0))
        
        # Row 5 - Scheduling
        ttk.Label(add_frame, text="Schedule:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        
        schedule_frame = ttk.Frame(add_frame)
        schedule_frame.grid(row=5, column=1, columnspan=3, padx=5, pady=2, sticky=tk.W)
        
        self.schedule_var = tk.BooleanVar()
        ttk.Checkbutton(schedule_frame, text="Schedule for later", variable=self.schedule_var,
                       command=self.on_schedule_change).pack(side=tk.LEFT)
        
        self.schedule_time_frame = ttk.Frame(schedule_frame)
        self.schedule_time_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(self.schedule_time_frame, text="Date:").pack(side=tk.LEFT)
        self.date_entry = ttk.Entry(self.schedule_time_frame, width=12)
        self.date_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Label(self.schedule_time_frame, text="Time:").pack(side=tk.LEFT)
        self.time_entry = ttk.Entry(self.schedule_time_frame, width=8)
        self.time_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.time_entry.insert(0, "12:00")
        
        # Row 6 - Buttons
        button_frame = ttk.Frame(add_frame)
        button_frame.grid(row=6, column=0, columnspan=4, pady=10)
        
        add_post_btn = ttk.Button(button_frame, text="Add Post", command=self.add_post, style="Action.TButton")
        add_post_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear", command=self.clear_post_form).pack(side=tk.LEFT, padx=5)
        
        # Post Now section
        ttk.Separator(button_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(button_frame, text="Headless", variable=self.headless_var).pack(side=tk.LEFT, padx=5)
        
        post_now_btn = ttk.Button(button_frame, text="Post Now", command=self.post_now, style="Action.TButton")
        post_now_btn.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(post_now_btn, "Post immediately without adding to queue")
        
        # Posts list
        list_frame = ttk.LabelFrame(posts_frame, text="Post Queue")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for posts with better column sizing
        columns = ("Subreddit", "Title", "Type", "Account", "Proxy", "Headless", "Status", "Scheduled")
        self.posts_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Configure columns with better proportions
        self.posts_tree.heading("Subreddit", text="Subreddit")
        self.posts_tree.column("Subreddit", width=100, minwidth=80)
        
        self.posts_tree.heading("Title", text="Title")
        self.posts_tree.column("Title", width=200, minwidth=150)
        
        self.posts_tree.heading("Type", text="Type")
        self.posts_tree.column("Type", width=50, minwidth=40)
        
        self.posts_tree.heading("Account", text="Account")
        self.posts_tree.column("Account", width=100, minwidth=80)
        
        self.posts_tree.heading("Proxy", text="Proxy")
        self.posts_tree.column("Proxy", width=50, minwidth=40)
        
        self.posts_tree.heading("Headless", text="Headless")
        self.posts_tree.column("Headless", width=60, minwidth=50)
        
        self.posts_tree.heading("Status", text="Status")
        self.posts_tree.column("Status", width=70, minwidth=60)
        
        self.posts_tree.heading("Scheduled", text="Scheduled")
        self.posts_tree.column("Scheduled", width=130, minwidth=100)
        
        scrollbar_posts = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.posts_tree.yview)
        self.posts_tree.configure(yscrollcommand=scrollbar_posts.set)
        
        self.posts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_posts.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Context menu for posts
        self.posts_menu = tk.Menu(self.root, tearoff=0, font=('Segoe UI', 9))
        self.posts_menu.add_command(label="Edit Post", command=self.edit_post)
        self.posts_menu.add_separator()
        self.posts_menu.add_command(label="Delete Post", command=self.delete_post)
        self.posts_tree.bind("<Button-3>", self.show_posts_menu)
        self.posts_tree.bind("<Button-1>", self.hide_all_menus)
        
        # Initialize UI state
        self.on_post_type_change()
        self.on_schedule_change()

    def setup_proxies_tab(self, notebook):
        """Setup proxy management tab"""
        proxies_frame = ttk.Frame(notebook)
        notebook.add(proxies_frame, text="Proxies")
        
        # Create main container with better spacing and scrolling
        main_container = ttk.Frame(proxies_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a paned window for resizable sections
        paned_window = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Add proxy section with scrolling
        left_canvas = tk.Canvas(paned_window, width=350)
        left_scrollbar = ttk.Scrollbar(paned_window, orient="vertical", command=left_canvas.yview)
        left_scrollable_frame = ttk.Frame(left_canvas)
        
        left_scrollable_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        
        left_canvas.create_window((0, 0), window=left_scrollable_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Add proxy section with improved layout
        add_frame = ttk.LabelFrame(left_scrollable_frame, text="Add New Proxy", padding=10)
        add_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        # Basic proxy info
        basic_frame = ttk.LabelFrame(add_frame, text="Basic Information", padding=5)
        basic_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(basic_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.proxy_host_entry = ttk.Entry(basic_frame, width=25)
        self.proxy_host_entry.grid(row=0, column=1, padx=5, pady=3, sticky=tk.W+tk.E)
        
        ttk.Label(basic_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.proxy_port_entry = ttk.Entry(basic_frame, width=25)
        self.proxy_port_entry.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W+tk.E)
        
        ttk.Label(basic_frame, text="Protocol:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.proxy_protocol_combo = ttk.Combobox(basic_frame, values=["http", "https", "socks4", "socks5"], 
                                               width=22, state="readonly")
        self.proxy_protocol_combo.set("http")
        self.proxy_protocol_combo.grid(row=2, column=1, padx=5, pady=3, sticky=tk.W+tk.E)
        self.create_tooltip(self.proxy_protocol_combo, "Select proxy protocol. SOCKS5 provides better anonymity and supports UDP traffic.")
        
        basic_frame.columnconfigure(1, weight=1)
        
        # Authentication (optional)
        auth_frame = ttk.LabelFrame(add_frame, text="Authentication (Optional)", padding=5)
        auth_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(auth_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.proxy_username_entry = ttk.Entry(auth_frame, width=25)
        self.proxy_username_entry.grid(row=0, column=1, padx=5, pady=3, sticky=tk.W+tk.E)
        
        ttk.Label(auth_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.proxy_password_entry = ttk.Entry(auth_frame, width=25, show="*")
        self.proxy_password_entry.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W+tk.E)
        
        auth_frame.columnconfigure(1, weight=1)
        
        # IP Rotation (optional)
        rotation_frame = ttk.LabelFrame(add_frame, text="IP Rotation (Optional)", padding=5)
        rotation_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(rotation_frame, text="Rotation URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.proxy_rotation_url_entry = ttk.Entry(rotation_frame, width=25)
        self.proxy_rotation_url_entry.grid(row=0, column=1, padx=5, pady=3, sticky=tk.W+tk.E)
        
        ttk.Button(rotation_frame, text="Test Rotation", command=self.rotate_ip).grid(row=1, column=0, columnspan=2, pady=5)
        
        rotation_frame.columnconfigure(1, weight=1)
        
        # Action buttons
        button_frame = ttk.Frame(add_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Add Proxy", command=self.add_proxy).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Import from File", command=self.import_proxies).pack(fill=tk.X, pady=2)
        
        # Proxy management section
        management_frame = ttk.LabelFrame(left_scrollable_frame, text="Proxy Management", padding=10)
        management_frame.pack(fill=tk.X, padx=10)
        
        ttk.Button(management_frame, text="Test All Proxies", command=self.test_all_proxies).pack(fill=tk.X, pady=2)
        ttk.Button(management_frame, text="Check Selected Proxy", command=self.check_proxy_with_location).pack(fill=tk.X, pady=2)
        ttk.Button(management_frame, text="Clear Failed Proxies", command=self.clear_failed_proxies).pack(fill=tk.X, pady=2)
        
        # Add left panel to paned window
        paned_window.add(left_canvas, weight=0)
        
        # Right side - Proxy list
        right_frame = ttk.Frame(paned_window)
        
        # Proxies list with improved header
        list_frame = ttk.LabelFrame(right_frame, text="Proxy List", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add right panel to paned window
        paned_window.add(right_frame, weight=1)
        
        # Treeview for proxies with better column sizing
        columns = ("URL", "Has Rotation", "Protocol", "Status", "Location", "Success", "Failures", "Last Used")
        self.proxies_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Configure columns with better proportions
        self.proxies_tree.heading("URL", text="URL")
        self.proxies_tree.column("URL", width=200, minwidth=150)
        
        self.proxies_tree.heading("Has Rotation", text="Rotation")
        self.proxies_tree.column("Has Rotation", width=70, minwidth=60)
        
        self.proxies_tree.heading("Protocol", text="Protocol")
        self.proxies_tree.column("Protocol", width=70, minwidth=60)
        
        self.proxies_tree.heading("Status", text="Status")
        self.proxies_tree.column("Status", width=70, minwidth=60)
        
        self.proxies_tree.heading("Location", text="Location")
        self.proxies_tree.column("Location", width=150, minwidth=100)
        
        self.proxies_tree.heading("Success", text="Success")
        self.proxies_tree.column("Success", width=60, minwidth=50)
        
        self.proxies_tree.heading("Failures", text="Failures")
        self.proxies_tree.column("Failures", width=60, minwidth=50)
        
        self.proxies_tree.heading("Last Used", text="Last Used")
        self.proxies_tree.column("Last Used", width=120, minwidth=100)
        
        scrollbar_proxies = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.proxies_tree.yview)
        self.proxies_tree.configure(yscrollcommand=scrollbar_proxies.set)
        
        self.proxies_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_proxies.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Context menu for proxies
        self.proxies_menu = tk.Menu(self.root, tearoff=0, font=('Segoe UI', 9))
        self.proxies_menu.add_command(label="Check Proxy & Location", command=self.check_proxy_with_location)
        self.proxies_menu.add_command(label="Test Proxy", command=self.test_selected_proxy)
        self.proxies_menu.add_command(label="Rotate IP", command=self.rotate_selected_proxy_ip)
        self.proxies_menu.add_separator()
        self.proxies_menu.add_command(label="Delete Proxy", command=self.delete_proxy)
        self.proxies_tree.bind("<Button-3>", self.show_proxies_menu)
        self.proxies_tree.bind("<Button-1>", self.hide_all_menus)

    def setup_scheduler_tab(self, notebook):
        """Setup scheduler control tab"""
        scheduler_frame = ttk.Frame(notebook)
        notebook.add(scheduler_frame, text="Scheduler")
        
        # Control section
        control_frame = ttk.LabelFrame(scheduler_frame, text="Scheduler Control")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.scheduler_status_var = tk.StringVar(value="Stopped")
        ttk.Label(control_frame, text="Status:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.scheduler_status_label = ttk.Label(control_frame, textvariable=self.scheduler_status_var, foreground="red", font=('Segoe UI', 10, 'bold'))
        self.scheduler_status_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Scheduler", command=self.start_scheduler, style="Action.TButton")
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(self.start_button, "Start the automated posting scheduler")
        
        self.stop_button = ttk.Button(button_frame, text="Stop Scheduler", command=self.stop_scheduler, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(self.stop_button, "Stop the automated posting scheduler")
        
        ttk.Button(button_frame, text="Reschedule Posts", command=self.reschedule_posts).pack(side=tk.LEFT, padx=5)
        self.create_tooltip(button_frame.winfo_children()[-1], "Reschedule all pending posts to future times for testing")
        
        # Status section
        status_frame = ttk.LabelFrame(scheduler_frame, text="Scheduler Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Statistics
        stats_frame = ttk.Frame(status_frame)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(stats_frame, text="Pending Posts:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.pending_posts_var = tk.StringVar(value="0")
        ttk.Label(stats_frame, textvariable=self.pending_posts_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_frame, text="Posts Completed:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.completed_posts_var = tk.StringVar(value="0")
        ttk.Label(stats_frame, textvariable=self.completed_posts_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_frame, text="Currently Posting:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.currently_posting_var = tk.StringVar(value="None")
        ttk.Label(stats_frame, textvariable=self.currently_posting_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_frame, text="Next Post:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.next_post_var = tk.StringVar(value="None")
        ttk.Label(stats_frame, textvariable=self.next_post_var).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Log display
        log_frame = ttk.LabelFrame(status_frame, text="Scheduler Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.scheduler_log = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.scheduler_log.yview)
        self.scheduler_log.configure(yscrollcommand=log_scrollbar.set)
        
        self.scheduler_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Settings section
        settings_frame = ttk.LabelFrame(scheduler_frame, text="Settings")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(settings_frame, text="Account cooldown (seconds):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.min_delay_var = tk.StringVar(value=str(self.poster.config["min_delay_between_posts"]))
        ttk.Entry(settings_frame, textvariable=self.min_delay_var, width=10).grid(row=0, column=1, padx=5, pady=2)
        
        # Add explanation
        explanation_text = "Account cooldown: Minimum time between posts from the same account\nScheduled posts will be made at their exact scheduled times"
        ttk.Label(settings_frame, text=explanation_text, font=('Segoe UI', 8), foreground="gray").grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(settings_frame, text="Save Settings", command=self.save_settings).grid(row=2, column=0, columnspan=2, pady=10)



    def on_post_type_change(self):
        """Handle post type change"""
        if self.post_type_var.get() == "text":
            self.text_content.pack(fill=tk.BOTH, expand=True)
            self.image_frame.pack_forget()
        else:
            self.text_content.pack_forget()
            self.image_frame.pack(fill=tk.X)

    def on_schedule_change(self):
        """Handle schedule checkbox change"""
        if self.schedule_var.get():
            for widget in self.schedule_time_frame.winfo_children():
                widget.configure(state=tk.NORMAL)
        else:
            for widget in self.schedule_time_frame.winfo_children():
                if isinstance(widget, ttk.Entry):
                    widget.configure(state=tk.DISABLED)

    def browse_images(self):
        """Browse for multiple image files"""
        filenames = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.webp"),
                ("All files", "*.*")
            ]
        )
        if filenames:
            # Add new images to the list, avoiding duplicates
            for filename in filenames:
                if filename not in self.selected_image_paths:
                    self.selected_image_paths.append(filename)
            self.update_image_listbox()
    
    def remove_selected_images(self):
        """Remove selected images from the list"""
        selected_indices = self.image_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Info", "Please select images to remove")
            return
        
        # Remove in reverse order to maintain indices
        for index in reversed(selected_indices):
            del self.selected_image_paths[index]
        
        self.update_image_listbox()
    
    def clear_all_images(self):
        """Clear all selected images"""
        self.selected_image_paths.clear()
        self.update_image_listbox()
    
    def update_image_listbox(self):
        """Update the image listbox display"""
        self.image_listbox.delete(0, tk.END)
        for i, path in enumerate(self.selected_image_paths, 1):
            # Show just the filename with index for better readability
            filename = os.path.basename(path)
            self.image_listbox.insert(tk.END, f"{i}. {filename}")
        
        # Update tooltip with full paths
        if self.selected_image_paths:
            tooltip_text = f"Selected {len(self.selected_image_paths)} images:\n" + "\n".join([f"{i}. {path}" for i, path in enumerate(self.selected_image_paths, 1)])
            try:
                self.create_tooltip(self.image_listbox, tooltip_text)
            except:
                pass  # Tooltip creation might fail, but it's not critical
    
    def browse_image(self):
        """Legacy method for backward compatibility - now calls browse_images"""
        self.browse_images()

    def add_account(self):
        """Add a new account"""
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
        
        if username in self.poster.accounts:
            messagebox.showerror("Error", "Account already exists")
            return
        
        # Get selected proxy
        selected_proxy = self.account_proxy_combo.get()
        use_proxy = self.use_proxy_for_account_var.get()
        
        # Show login confirmation UI
        self.current_username = username
        self.login_status_label.config(text=f"Please login to Reddit account: {username}")
        self.login_confirm_frame.grid()
        self.confirm_login_button.config(state=tk.NORMAL)
        
        # Run in thread to avoid blocking UI
        def add_account_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Create a future for the login confirmation
                self.login_future = loop.create_future()
                
                async def login_callback(message):
                    # Wait for the GUI button to be clicked
                    await self.login_future
                
                # Pass proxy selection to add_account
                success = loop.run_until_complete(self.poster.add_account(
                    username, 
                    use_proxy=use_proxy,
                    preferred_proxy=selected_proxy if selected_proxy != "No proxy" else None,
                    login_callback=login_callback
                ))
                if success:
                    self.root.after(0, lambda: [
                        messagebox.showinfo("Success", f"Account {username} added successfully"),
                        self.refresh_accounts(),
                        self.clear_account_form(),
                        self.hide_login_confirm()
                    ])
                else:
                    self.root.after(0, lambda: [
                        messagebox.showerror("Error", f"Failed to add account {username}"),
                        self.hide_login_confirm()
                    ])
            except Exception as e:
                import traceback
                error_details = f"Error adding account: {e}\n\nFull traceback:\n{traceback.format_exc()}"
                print(error_details)  # Print to console for debugging
                self.root.after(0, lambda: [
                    messagebox.showerror("Error", f"Error adding account: {e}"),
                    self.hide_login_confirm()
                ])
            finally:
                loop.close()
        
        self.account_thread = threading.Thread(target=add_account_thread, daemon=True)
        self.account_thread.start()

    def confirm_login(self):
        """Confirm that login is complete"""
        if hasattr(self, 'login_future') and not self.login_future.done():
            self.login_future.set_result(True)
        self.confirm_login_button.config(state=tk.DISABLED)
        self.login_status_label.config(text="Login confirmed, processing...")

    def hide_login_confirm(self):
        """Hide the login confirmation UI"""
        self.login_confirm_frame.grid_remove()
        if hasattr(self, 'current_username'):
            delattr(self, 'current_username')
        if hasattr(self, 'login_future'):
            delattr(self, 'login_future')

    def clear_account_form(self):
        """Clear the account form"""
        self.username_entry.delete(0, tk.END)
        self.account_proxy_combo.set("")
        self.use_proxy_for_account_var.set(True)

    def show_accounts_menu(self, event):
        """Show context menu for accounts"""
        # Hide any existing menus first
        self.hide_all_menus()
        
        item = self.accounts_tree.identify_row(event.y)
        if item:
            self.accounts_tree.selection_set(item)
            self.accounts_menu.post(event.x_root, event.y_root)
            self.active_menus.append(self.accounts_menu)
            
            # Auto-hide menu after a delay if no interaction
            self.root.after(5000, lambda: self.safe_hide_menu(self.accounts_menu))

    def edit_account_proxy(self):
        """Edit proxy settings for selected account"""
        selection = self.accounts_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        username = self.accounts_tree.item(item)['values'][0]
        
        if username not in self.poster.accounts:
            return
        
        # Create a dialog for editing proxy settings
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Proxy Settings - {username}")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Current account
        account = self.poster.accounts[username]
        
        # Proxy selection
        ttk.Label(dialog, text="Preferred Proxy:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        proxy_var = tk.StringVar()
        proxy_combo = ttk.Combobox(dialog, textvariable=proxy_var, width=40, state="readonly")
        proxy_list = ["No proxy"] + list(self.poster.proxies.keys())
        proxy_combo['values'] = proxy_list
        proxy_combo.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W+tk.E)
        
        # Set current value
        current_proxy = account.preferred_proxy if account.preferred_proxy else "No proxy"
        proxy_var.set(current_proxy)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=1, column=0, columnspan=2, pady=20)
        
        def save_changes():
            new_proxy = proxy_var.get()
            if new_proxy == "No proxy":
                account.preferred_proxy = None
            else:
                account.preferred_proxy = new_proxy
            
            self.poster._save_accounts()
            self.refresh_accounts()
            dialog.destroy()
            messagebox.showinfo("Success", f"Proxy settings updated for {username}")
        
        def cancel_changes():
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel_changes).pack(side=tk.LEFT, padx=5)
        
        # Configure column weight for resizing
        dialog.columnconfigure(1, weight=1)

    def remove_account(self):
        """Remove selected account"""
        selection = self.accounts_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        username = self.accounts_tree.item(item)['values'][0]
        
        if messagebox.askyesno("Confirm", f"Remove account '{username}'?\nThis will delete all stored data for this account."):
            if username in self.poster.accounts:
                del self.poster.accounts[username]
                self.poster._save_accounts()
                self.refresh_accounts()
                messagebox.showinfo("Success", f"Account '{username}' removed successfully")

    def add_post(self):
        """Add a new post"""
        subreddit = self.subreddit_entry.get().strip()
        title = self.title_entry.get().strip()
        account = self.account_combo.get()
        
        if not all([subreddit, title, account]):
            messagebox.showerror("Error", "Please fill in subreddit, title, and account")
            return
        
        # Get content based on type
        post_type = self.post_type_var.get()
        if post_type == "text":
            content = self.text_content.get("1.0", tk.END).strip()
        else:
            # Handle multiple images
            if not self.selected_image_paths:
                messagebox.showerror("Error", "Please select at least one image")
                return
            
            # Verify all image files exist
            missing_files = []
            for path in self.selected_image_paths:
                if not Path(path).exists():
                    missing_files.append(os.path.basename(path))
            
            if missing_files:
                messagebox.showerror("Error", f"Image files not found: {', '.join(missing_files)}")
                return
            
            # Join paths with semicolon separator
            content = ';'.join(self.selected_image_paths)
        
        # Get scheduled time
        scheduled_time = None
        if self.schedule_var.get():
            try:
                date_str = self.date_entry.get()
                time_str = self.time_entry.get()
                datetime_str = f"{date_str} {time_str}"
                scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror("Error", "Invalid date/time format")
                return
        
        # Add post
        self.poster.add_post(
            subreddit=subreddit,
            title=title,
            content=content,
            post_type=post_type,
            nsfw=self.nsfw_var.get(),
            account_name=account,
            scheduled_time=scheduled_time,
            use_proxy=self.use_proxy_for_post_var.get(),
            headless=self.headless_for_post_var.get()
        )
        
        messagebox.showinfo("Success", "Post added to queue")
        self.refresh_posts()
        self.clear_post_form()

    def clear_post_form(self):
        """Clear the post form"""
        self.subreddit_entry.delete(0, tk.END)
        self.title_entry.delete(0, tk.END)
        self.text_content.delete("1.0", tk.END)
        self.clear_all_images()
        self.nsfw_var.set(False)
        self.use_proxy_for_post_var.set(True)
        self.headless_for_post_var.set(True)
        self.schedule_var.set(False)
        self.on_schedule_change()

    def post_now(self):
        """Post immediately without scheduling"""
        subreddit = self.subreddit_entry.get().strip()
        title = self.title_entry.get().strip()
        account = self.account_combo.get()
        
        if not all([subreddit, title, account]):
            messagebox.showerror("Error", "Please fill in subreddit, title, and account")
            return
        
        # Get content based on type
        post_type = self.post_type_var.get()
        if post_type == "text":
            content = self.text_content.get("1.0", tk.END).strip()
        else:
            # Handle multiple images
            if not self.selected_image_paths:
                messagebox.showerror("Error", "Please select at least one image")
                return
            
            # Verify all image files exist
            missing_files = []
            for path in self.selected_image_paths:
                if not Path(path).exists():
                    missing_files.append(os.path.basename(path))
            
            if missing_files:
                messagebox.showerror("Error", f"Image files not found: {', '.join(missing_files)}")
                return
            
            # Join paths with semicolon separator
            content = ';'.join(self.selected_image_paths)
        
        headless = self.headless_for_post_var.get()
        
        # Confirm before posting
        if not messagebox.askyesno("Confirm", f"Post '{title}' to r/{subreddit} now?\nHeadless: {headless}"):
            return
        
        # Run in thread to avoid blocking UI
        def post_now_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(self.poster.post_now(
                    subreddit=subreddit,
                    title=title,
                    content=content,
                    post_type=post_type,
                    nsfw=self.nsfw_var.get(),
                    account_name=account,
                    headless=headless,
                    use_proxy=self.use_proxy_for_post_var.get()
                ))
                
                if success:
                    self.root.after(0, lambda: [
                        messagebox.showinfo("Success", f"Post '{title}' posted successfully to r/{subreddit}"),
                        self.clear_post_form()
                    ])
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to post '{title}' to r/{subreddit}"))
            except Exception as e:
                import traceback
                error_details = f"Error posting: {e}\n\nFull traceback:\n{traceback.format_exc()}"
                print(error_details)  # Print to console for debugging
                error_msg = str(e)  # Capture the error message
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error posting: {error_msg}"))
            finally:
                loop.close()
        
        threading.Thread(target=post_now_thread, daemon=True).start()

    def delete_post(self):
        """Delete selected post"""
        selection = self.posts_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.posts_tree.index(item)
        
        if messagebox.askyesno("Confirm", "Delete this post?"):
            del self.poster.posts[index]
            self.poster._save_posts()
            self.refresh_posts()
            
    def edit_post(self):
        """Edit selected post"""
        selection = self.posts_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.posts_tree.index(item)
        
        if index >= len(self.poster.posts):
            return
            
        post = self.poster.posts[index]
        
        # Fill the form with post data
        self.subreddit_entry.delete(0, tk.END)
        self.subreddit_entry.insert(0, post.subreddit)
        
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, post.title)
        
        self.post_type_var.set(post.post_type)
        self.on_post_type_change()
        
        if post.post_type == "text":
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", post.content)
        else:
            # Handle multiple images
            self.clear_all_images()
            if post.content:
                image_paths = [path.strip() for path in post.content.split(';') if path.strip()]
                self.selected_image_paths = image_paths
                self.update_image_listbox()
            
        self.nsfw_var.set(post.nsfw)
        
        # Set account
        if post.account_name:
            self.account_combo.set(post.account_name)
            
        # Set scheduling
        if post.scheduled_time:
            self.schedule_var.set(True)
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, post.scheduled_time.strftime("%Y-%m-%d"))
            self.time_entry.delete(0, tk.END)
            self.time_entry.insert(0, post.scheduled_time.strftime("%H:%M"))
        else:
            self.schedule_var.set(False)
            
        self.on_schedule_change()
        
        # Remove the original post
        del self.poster.posts[index]
        self.poster._save_posts()
        self.refresh_posts()
        
        # Switch to Posts tab
        self.notebook.select(1)  # Posts tab is index 1
        
        messagebox.showinfo("Edit Mode", "Post loaded for editing. Make your changes and click 'Add Post' to save.")

    def show_posts_menu(self, event):
        """Show context menu for posts"""
        # Hide any existing menus first
        self.hide_all_menus()
        
        item = self.posts_tree.identify_row(event.y)
        if item:
            self.posts_tree.selection_set(item)
            self.posts_menu.post(event.x_root, event.y_root)
            self.active_menus.append(self.posts_menu)
            
            # Auto-hide menu after a delay if no interaction
            self.root.after(5000, lambda: self.safe_hide_menu(self.posts_menu))

    def start_scheduler(self):
        """Start the scheduler"""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        self.scheduler_status_var.set("Running")
        self.scheduler_status_label.configure(foreground="green")
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        
        # Add initial log message
        self.add_scheduler_log("Scheduler started")
        
        # Start periodic status updates
        self.update_scheduler_status()
        
        def scheduler_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.poster.run_scheduler())
            except Exception as e:
                self.add_scheduler_log(f"Scheduler error: {e}")
                print(f"Scheduler error: {e}")
            finally:
                loop.close()
                self.scheduler_running = False
                self.root.after(0, self.scheduler_stopped)
        
        self.scheduler_thread = threading.Thread(target=scheduler_thread, daemon=True)
        self.scheduler_thread.start()

    def stop_scheduler(self):
        """Stop the scheduler"""
        self.scheduler_running = False
        self.add_scheduler_log("Scheduler stop requested")
        self.scheduler_stopped()

    def scheduler_stopped(self):
        """Handle scheduler stopped"""
        self.scheduler_status_var.set("Stopped")
        self.scheduler_status_label.configure(foreground="red")
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.add_scheduler_log("Scheduler stopped")
    
    def add_scheduler_log(self, message):
        """Add a message to the scheduler log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.scheduler_log.configure(state=tk.NORMAL)
        self.scheduler_log.insert(tk.END, log_message)
        self.scheduler_log.configure(state=tk.DISABLED)
        self.scheduler_log.see(tk.END)
    
    def update_scheduler_status(self):
        """Update scheduler status information"""
        if not self.scheduler_running:
            return
        
        try:
            # Update statistics
            pending_posts = len([p for p in self.poster.posts if p.status == "pending"])
            completed_posts = len([p for p in self.poster.posts if p.status == "posted"])
            currently_posting = [p for p in self.poster.posts if p.status == "posting"]
            
            self.pending_posts_var.set(str(pending_posts))
            self.completed_posts_var.set(str(completed_posts))
            
            # Show currently posting posts
            if currently_posting:
                posting_titles = [f"{p.title[:20]}..." for p in currently_posting]
                self.currently_posting_var.set(f"{len(currently_posting)} posts: {', '.join(posting_titles)}")
            else:
                self.currently_posting_var.set("None")
            
            # Find next scheduled post
            now = datetime.now()
            next_posts = [p for p in self.poster.posts 
                         if p.status == "pending" and p.scheduled_time and p.scheduled_time > now]
            
            if next_posts:
                next_post = min(next_posts, key=lambda x: x.scheduled_time)
                next_time = next_post.scheduled_time.strftime("%Y-%m-%d %H:%M:%S")
                time_until = next_post.scheduled_time - now
                self.next_post_var.set(f"{next_time} ({time_until}) - {next_post.title[:20]}...")
            else:
                self.next_post_var.set("None scheduled")
            
        except Exception as e:
            self.add_scheduler_log(f"Status update error: {e}")
        
        # Schedule next update
        if self.scheduler_running:
            self.root.after(5000, self.update_scheduler_status)  # Update every 5 seconds
    
    def reschedule_posts(self):
        """Reschedule pending posts to future times"""
        try:
            count = self.poster.reschedule_pending_posts_to_future(5)  # Start 5 minutes from now
            if count > 0:
                messagebox.showinfo("Success", f"Rescheduled {count} posts to future times")
                self.refresh_posts()  # Refresh the posts display
                self.add_scheduler_log(f"Rescheduled {count} posts to future times")
            else:
                messagebox.showinfo("Info", "No pending posts to reschedule")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reschedule posts: {e}")
            
    def create_tooltip(self, widget, text):
        """Create a robust tooltip for a widget"""
        # Initialize tooltip tracking if not exists
        if not hasattr(self, 'active_tooltips'):
            self.active_tooltips = []
        
        class ToolTip:
            def __init__(self, widget, text, parent_gui):
                self.widget = widget
                self.text = text
                self.parent_gui = parent_gui
                self.tooltip_window = None
                self.show_timer = None
                self.hide_timer = None
                
                # Bind events
                self.widget.bind("<Enter>", self.on_enter, add="+")
                self.widget.bind("<Leave>", self.on_leave, add="+")
                self.widget.bind("<Button-1>", self.hide_tooltip, add="+")
                self.widget.bind("<Key>", self.hide_tooltip, add="+")
                
            def on_enter(self, event=None):
                # Cancel any pending hide timer
                if self.hide_timer:
                    self.widget.after_cancel(self.hide_timer)
                    self.hide_timer = None
                
                # Schedule tooltip to show after a short delay
                if not self.tooltip_window:
                    self.show_timer = self.widget.after(500, lambda: self.show_tooltip(event))
                
            def on_leave(self, event=None):
                # Cancel show timer if tooltip hasn't appeared yet
                if self.show_timer:
                    self.widget.after_cancel(self.show_timer)
                    self.show_timer = None
                
                # Schedule tooltip to hide after a short delay
                if self.tooltip_window:
                    self.hide_timer = self.widget.after(100, self.hide_tooltip)
                
            def show_tooltip(self, event=None):
                if self.tooltip_window:
                    return
                
                try:
                    # Get widget position
                    x = self.widget.winfo_rootx() + 20
                    y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
                    
                    # Create tooltip window
                    self.tooltip_window = tk.Toplevel(self.widget)
                    self.tooltip_window.wm_overrideredirect(True)
                    self.tooltip_window.wm_geometry(f"+{x}+{y}")
                    
                    # Make tooltip stay on top but not steal focus
                    self.tooltip_window.attributes('-topmost', True)
                    
                    # Create label with text
                    label = tk.Label(
                        self.tooltip_window, 
                        text=self.text, 
                        background="lightyellow",
                        foreground="black",
                        relief="solid", 
                        borderwidth=1, 
                        font=("Segoe UI", 8),
                        padx=4,
                        pady=2
                    )
                    label.pack()
                    
                    # Add to active tooltips list
                    if self in self.parent_gui.active_tooltips:
                        self.parent_gui.active_tooltips.remove(self)
                    self.parent_gui.active_tooltips.append(self)
                    
                    # Bind tooltip window events
                    self.tooltip_window.bind("<Enter>", self.on_tooltip_enter)
                    self.tooltip_window.bind("<Leave>", self.on_tooltip_leave)
                    
                except Exception:
                    # If tooltip creation fails, clean up
                    self.hide_tooltip()
                
            def on_tooltip_enter(self, event=None):
                # Cancel hide timer if mouse enters tooltip
                if self.hide_timer:
                    self.widget.after_cancel(self.hide_timer)
                    self.hide_timer = None
                    
            def on_tooltip_leave(self, event=None):
                # Hide tooltip when mouse leaves tooltip window
                self.hide_tooltip()
                
            def hide_tooltip(self, event=None):
                # Cancel any pending timers
                if self.show_timer:
                    self.widget.after_cancel(self.show_timer)
                    self.show_timer = None
                if self.hide_timer:
                    self.widget.after_cancel(self.hide_timer)
                    self.hide_timer = None
                
                # Destroy tooltip window
                if self.tooltip_window:
                    try:
                        self.tooltip_window.destroy()
                    except:
                        pass
                    self.tooltip_window = None
                    
                # Remove from active tooltips list
                if self in self.parent_gui.active_tooltips:
                    self.parent_gui.active_tooltips.remove(self)
        
        # Create and store tooltip instance
        tooltip_instance = ToolTip(widget, text, self)
        
        # Store reference to tooltip on widget for cleanup
        if not hasattr(widget, '_tooltips'):
            widget._tooltips = []
        widget._tooltips.append(tooltip_instance)
        
    def setup_status_bar(self):
        """Setup status bar at the bottom of the window"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        # Status text
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.status_bar, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Quick stats
        self.quick_stats_var = tk.StringVar(value="")
        stats_label = ttk.Label(self.status_bar, textvariable=self.quick_stats_var, relief=tk.SUNKEN, anchor=tk.E)
        stats_label.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Update status bar periodically
        self.update_status_bar()
        
    def update_status_bar(self):
        """Update the status bar information"""
        try:
            accounts_count = len(self.poster.accounts)
            posts_count = len(self.poster.posts)
            pending_posts = len([p for p in self.poster.posts if p.status == "pending"])
            
            scheduler_status = "Running" if self.scheduler_running else "Stopped"
            
            self.status_var.set(f"Scheduler: {scheduler_status}")
            self.quick_stats_var.set(f"Accounts: {accounts_count} | Posts: {posts_count} | Pending: {pending_posts}")
            
        except Exception as e:
            self.status_var.set("Error updating status")
            
        # Schedule next update
        self.root.after(5000, self.update_status_bar)

    def save_settings(self):
        """Save scheduler settings"""
        try:
            # Only save the account cooldown (min_delay_between_posts)
            # This is the minimum time between posts from the same account
            self.poster.config["min_delay_between_posts"] = int(self.min_delay_var.get())
            
            with open(self.poster.config_file, 'w') as f:
                json.dump(self.poster.config, f, indent=2)
            
            messagebox.showinfo("Success", "Account cooldown setting saved")
        except ValueError:
            messagebox.showerror("Error", "Invalid cooldown value")

    def load_account_manually(self):
        """Load an account manually for browser usage"""
        account_name = self.manual_account_combo.get()
        if not account_name:
            messagebox.showerror("Error", "Please select an account")
            return
        
        if account_name not in self.poster.accounts:
            messagebox.showerror("Error", f"Account '{account_name}' not found")
            return
        
        # Close any existing manual session
        self.close_manual_session()
        
        def load_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                self.root.after(0, lambda: self.manual_session_status.config(text="Loading account...", foreground="blue"))
                
                # Create browser session with account
                browser_instance, account = loop.run_until_complete(self.poster.create_browser_session(account_name, use_proxy=True, headless=False))
                
                # Start the browser manually (not using context manager to keep it alive)
                async def setup_browser():
                    # Import the necessary modules
                    from camoufox.async_api import AsyncNewBrowser
                    from playwright.async_api import async_playwright
                    
                    # Start playwright and create browser with visible window
                    playwright = await async_playwright().start()
                    
                    # Override headless setting for manual use
                    launch_options = browser_instance.launch_options.copy()
                    launch_options["headless"] = False  # Force visible browser for manual use
                    
                    browser = await AsyncNewBrowser(playwright, **launch_options)
                    page = await browser.new_page()
                    
                    # Set cookies for the account
                    if account and hasattr(account, 'cookies') and account.cookies:
                        cookie_list = [
                            {"name": name, "value": value, "domain": ".reddit.com", "path": "/"}
                            for name, value in account.cookies.items()
                        ]
                        await page.context.add_cookies(cookie_list)
                    
                    # Navigate to Reddit
                    await page.goto("https://www.reddit.com", wait_until="domcontentloaded")
                    
                    return browser, page, playwright
                
                browser, page, playwright = loop.run_until_complete(setup_browser())
                
                # Store session info
                self.manual_browser = browser
                self.manual_page = page
                self.manual_playwright = playwright
                self.manual_loop = loop  # Store the event loop for later use
                self.manual_account_name = account_name
                
                self.root.after(0, lambda: [
                    self.manual_session_status.config(text=f"Active session: {account_name}", foreground="green"),
                    self.update_cookies_btn.config(state=tk.NORMAL),
                    self.close_session_btn.config(state=tk.NORMAL),
                    messagebox.showinfo("Success", f"Account '{account_name}' loaded successfully!\nBrowser is ready for manual use.")
                ])
                
            except Exception as e:
                error_msg = str(e)  # Capture the error message
                self.root.after(0, lambda: [
                    self.manual_session_status.config(text="Failed to load account", foreground="red"),
                    messagebox.showerror("Error", f"Failed to load account: {error_msg}")
                ])
            finally:
                # Don't close the loop here as we need it for the manual session
                # The loop will be closed when the session is closed
                pass
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def update_account_cookies(self):
        """Update cookies for the currently loaded account"""
        if not self.manual_browser or not self.manual_page or not self.manual_account_name:
            messagebox.showerror("Error", "No active manual session")
            return
        
        # Show updating status immediately
        self.manual_session_status.config(text="Updating cookies...", foreground="blue")
        
        def update_in_thread():
            try:
                # Create a simple async function to get cookies
                async def get_cookies_simple():
                    return await self.manual_page.context.cookies()
                
                # Run in a new thread with a new event loop
                import concurrent.futures
                
                def run_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(get_cookies_simple())
                    finally:
                        loop.close()
                
                # Use ThreadPoolExecutor to run the async function
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    cookies = future.result(timeout=10)
                
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                
                # Update account cookies
                account = self.poster.accounts[self.manual_account_name]
                account.cookies = cookie_dict
                account.last_used = datetime.now()
                
                # Save accounts
                self.poster._save_accounts()
                
                self.root.after(0, lambda: [
                    self.manual_session_status.config(text=f"Cookies updated: {self.manual_account_name}", foreground="green"),
                    messagebox.showinfo("Success", f"Cookies updated for '{self.manual_account_name}'!\nFound {len(cookie_dict)} cookies."),
                    self.refresh_accounts()
                ])
                
            except Exception as e:
                error_msg = str(e)  # Capture the error message
                self.root.after(0, lambda: [
                    self.manual_session_status.config(text="Failed to update cookies", foreground="red"),
                    messagebox.showerror("Error", f"Failed to update cookies: {error_msg}")
                ])
        
        # Run the update in a separate thread
        threading.Thread(target=update_in_thread, daemon=True).start()
    
    def close_manual_session(self):
        """Close the manual browser session"""
        if self.manual_browser:
            try:
                # Close browser in a separate thread
                def close_thread():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Close browser and playwright
                        loop.run_until_complete(self.manual_browser.close())
                        if hasattr(self, 'manual_playwright') and self.manual_playwright:
                            loop.run_until_complete(self.manual_playwright.stop())
                        # Close the manual loop if it exists
                        if hasattr(self, 'manual_loop') and self.manual_loop and not self.manual_loop.is_closed():
                            self.manual_loop.call_soon_threadsafe(self.manual_loop.stop)
                    except:
                        pass
                    finally:
                        loop.close()
                
                threading.Thread(target=close_thread, daemon=True).start()
            except:
                pass
        
        # Reset session variables
        self.manual_browser = None
        self.manual_page = None
        self.manual_playwright = None
        self.manual_loop = None
        self.manual_account_name = None
        self.update_cookies_btn.config(state=tk.DISABLED)
        self.close_session_btn.config(state=tk.DISABLED)
        self.manual_session_status.config(text="No active session", foreground="gray")

    def refresh_accounts(self):
        """Refresh accounts list"""
        try:
            # Clear existing items
            for item in self.accounts_tree.get_children():
                self.accounts_tree.delete(item)
            
            print(f"DEBUG: Found {len(self.poster.accounts)} accounts to display")
            
            # Add accounts
            for username, account in self.poster.accounts.items():
                try:
                    print(f"DEBUG: Processing account {username}, type: {type(account)}")
                    
                    # Count posts for this account
                    post_count = len([p for p in self.poster.posts if p.account_name == username])
                    
                    last_used = account.last_used.strftime("%Y-%m-%d %H:%M") if account.last_used else "Never"
                    
                    # Get proxy display info
                    proxy_info = "No proxy"
                    if hasattr(account, 'use_proxy') and account.use_proxy and account.preferred_proxy:
                        proxy_data = self.poster.proxies.get(account.preferred_proxy)
                        if proxy_data:
                            proxy_info = f"{proxy_data.host}:{proxy_data.port}"
                        else:
                            proxy_info = account.preferred_proxy
                    elif account.preferred_proxy:
                        proxy_data = self.poster.proxies.get(account.preferred_proxy)
                        if proxy_data:
                            proxy_info = f"{proxy_data.host}:{proxy_data.port}"
                        else:
                            proxy_info = account.preferred_proxy
                    
                    self.accounts_tree.insert("", tk.END, values=(
                        username, account.status, post_count, proxy_info, last_used
                    ))
                except Exception as e:
                    print(f"Error processing account {username}: {e}")
            
            # Update account combo
            try:
                account_names = list(self.poster.accounts.keys())
                self.account_combo['values'] = account_names
                if account_names and not self.account_combo.get():
                    self.account_combo.set(account_names[0])
            except:
                pass
            
            # Update manual account combo
            try:
                account_names = list(self.poster.accounts.keys())
                self.manual_account_combo['values'] = account_names
                if account_names and not self.manual_account_combo.get():
                    self.manual_account_combo.set(account_names[0])
            except:
                pass
            
            # Update proxy combo for account creation
            try:
                proxy_list = ["No proxy"] + [f"{p.host}:{p.port}" for p in self.poster.proxies.values()]
                self.account_proxy_combo['values'] = proxy_list
                if not self.account_proxy_combo.get():
                    self.account_proxy_combo.set("No proxy")
            except:
                pass
                
        except Exception as e:
            print(f"Error refreshing accounts: {e}")

    def refresh_posts(self):
        """Refresh posts list"""
        try:
            # Clear existing items
            for item in self.posts_tree.get_children():
                self.posts_tree.delete(item)
            
            # Add posts
            for post in self.poster.posts:
                try:
                    scheduled = post.scheduled_time.strftime("%Y-%m-%d %H:%M") if post.scheduled_time else "Now"
                    proxy_status = "Yes" if getattr(post, 'use_proxy', True) else "No"
                    headless_status = "Yes" if getattr(post, 'headless', True) else "No"
                    
                    # Truncate title if too long
                    display_title = post.title[:30] + "..." if len(post.title) > 30 else post.title
                    
                    # Show image count for image posts
                    post_type_display = post.post_type
                    if post.post_type == "image" and post.content:
                        image_count = len(post.image_paths)
                        post_type_display = f"image ({image_count})"
                    
                    self.posts_tree.insert("", tk.END, values=(
                        post.subreddit, display_title, post_type_display, 
                        post.account_name, proxy_status, headless_status, post.status, scheduled
                    ))
                except Exception as e:
                    print(f"Error processing post: {e}")
                    
        except Exception as e:
            print(f"Error refreshing posts: {e}")

    def add_proxy(self):
        """Add a new proxy"""
        host = self.proxy_host_entry.get().strip()
        port = self.proxy_port_entry.get().strip()
        protocol = self.proxy_protocol_combo.get()
        username = self.proxy_username_entry.get().strip() or None
        password = self.proxy_password_entry.get().strip() or None
        rotation_url = self.proxy_rotation_url_entry.get().strip() or None
        
        try:
            if host and port:
                # Add proxy with all fields
                port = int(port)
                self.poster.add_proxy(host, port, username, password, rotation_url, protocol)
                messagebox.showinfo("Success", "Proxy added successfully")
                self.refresh_proxies()
                self.clear_proxy_form()
            else:
                messagebox.showerror("Error", "Please enter host and port")
                return
            
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
        except Exception as e:
            messagebox.showerror("Error", f"Error adding proxy: {e}")

    def clear_proxy_form(self):
        """Clear proxy form"""
        self.proxy_host_entry.delete(0, tk.END)
        self.proxy_port_entry.delete(0, tk.END)
        self.proxy_username_entry.delete(0, tk.END)
        self.proxy_password_entry.delete(0, tk.END)
        self.proxy_rotation_url_entry.delete(0, tk.END)
        self.proxy_protocol_combo.set("http")

    def rotate_ip(self):
        """Rotate IP using the rotation URL"""
        rotation_url = self.proxy_rotation_url_entry.get().strip()
        if not rotation_url:
            messagebox.showerror("Error", "Please enter a rotation URL")
            return
        
        def rotate_thread():
            try:
                import requests
                response = requests.get(rotation_url, timeout=10)
                if response.status_code == 200:
                    self.root.after(0, lambda: messagebox.showinfo("Success", "IP rotation successful"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Rotation failed: HTTP {response.status_code}"))
            except Exception as e:
                error_msg = str(e)  # Capture the error message
                self.root.after(0, lambda: messagebox.showerror("Error", f"Rotation failed: {error_msg}"))
        
        threading.Thread(target=rotate_thread, daemon=True).start()

    def import_proxies(self):
        """Import proxies from file"""
        filename = filedialog.askopenfilename(
            title="Select Proxy File",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        if filename:
            count = self.poster.import_proxies_from_file(filename)
            messagebox.showinfo("Success", f"Imported {count} proxies")
            self.refresh_proxies()

    def test_all_proxies(self):
        """Test all proxies"""
        if not self.poster.proxies:
            messagebox.showwarning("Warning", "No proxies to test")
            return
        
        # Create progress dialog
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Testing All Proxies")
        progress_dialog.geometry("350x150")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        progress_dialog.resizable(False, False)
        
        # Center the dialog
        progress_dialog.update_idletasks()
        x = (progress_dialog.winfo_screenwidth() // 2) - (progress_dialog.winfo_width() // 2)
        y = (progress_dialog.winfo_screenheight() // 2) - (progress_dialog.winfo_height() // 2)
        progress_dialog.geometry(f"+{x}+{y}")
        
        # Progress content
        ttk.Label(progress_dialog, text="Testing All Proxies", font=("Arial", 12, "bold")).pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_dialog, variable=progress_var, maximum=100)
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        
        status_label = ttk.Label(progress_dialog, text="Initializing...", foreground="blue")
        status_label.pack(pady=5)
        
        count_label = ttk.Label(progress_dialog, text="", foreground="gray")
        count_label.pack(pady=2)
        
        def test_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                total_proxies = len(self.poster.proxies)
                tested = 0
                
                # Update progress as we test each proxy
                async def progress_callback(current, total, proxy_url):
                    nonlocal tested
                    tested = current
                    progress = (current / total) * 100
                    self.root.after(0, lambda: [
                        progress_var.set(progress),
                        status_label.config(text=f"Testing: {proxy_url}"),
                        count_label.config(text=f"{current}/{total} proxies tested")
                    ])
                
                # Test all proxies with progress callback
                loop.run_until_complete(self.poster.test_all_proxies_with_progress(progress_callback))
                
                # Close progress dialog and show results
                self.root.after(0, lambda: [
                    progress_dialog.destroy(),
                    messagebox.showinfo("Complete", f"Proxy testing completed!\nTested {total_proxies} proxies."),
                    self.refresh_proxies()
                ])
            except Exception as e:
                self.root.after(0, lambda: [
                    progress_dialog.destroy(),
                    messagebox.showerror("Error", f"Error testing proxies: {e}")
                ])
            finally:
                loop.close()
        
        threading.Thread(target=test_thread, daemon=True).start()

    def test_selected_proxy(self):
        """Test selected proxy"""
        selection = self.proxies_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        proxy_url = self.proxies_tree.item(item)['values'][0]
        
        # Find the proxy by URL
        proxy = None
        for pid, p in self.poster.proxies.items():
            if p.url == proxy_url:
                proxy = p
                break
        
        if not proxy:
            return
        
        def test_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(self.poster.test_proxy(proxy))
                result = "working" if success else "failed"
                self.root.after(0, lambda: [
                    messagebox.showinfo("Test Result", f"Proxy is {result}"),
                    self.refresh_proxies()
                ])
            except Exception as e:
                error_msg = str(e)  # Capture the error message
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error testing proxy: {error_msg}"))
            finally:
                loop.close()
        
        threading.Thread(target=test_thread, daemon=True).start()

    def delete_proxy(self):
        """Delete selected proxy"""
        selection = self.proxies_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.proxies_tree.item(item)['values']
        proxy_url = values[0]  # URL is the first column
        
        if messagebox.askyesno("Confirm", f"Delete proxy {proxy_url}?"):
            # Find proxy ID by URL
            proxy_id = None
            for pid, proxy in self.poster.proxies.items():
                if proxy.url == proxy_url:
                    proxy_id = pid
                    break
            
            if proxy_id:
                self.poster.remove_proxy(proxy_id)
                self.refresh_proxies()

    def rotate_selected_proxy_ip(self):
        """Rotate IP for selected proxy"""
        selection = self.proxies_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.proxies_tree.item(item)['values']
        proxy_url = values[0]  # URL is the first column
        
        # Find proxy ID by URL
        proxy_id = None
        for pid, proxy in self.poster.proxies.items():
            if proxy.url == proxy_url:
                proxy_id = pid
                break
        
        if not proxy_id:
            messagebox.showerror("Error", "Proxy not found")
            return
        
        def rotate_thread():
            success = self.poster.rotate_proxy_ip(proxy_id)
            if success:
                self.root.after(0, lambda: messagebox.showinfo("Success", f"IP rotated for proxy {proxy_url}"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to rotate IP for proxy {proxy_url}"))
        
        threading.Thread(target=rotate_thread, daemon=True).start()

    def clear_failed_proxies(self):
        """Clear all failed proxies"""
        failed_proxies = [pid for pid, p in self.poster.proxies.items() if p.status == "failed"]
        
        if not failed_proxies:
            messagebox.showinfo("Info", "No failed proxies to clear")
            return
        
        if messagebox.askyesno("Confirm", f"Delete {len(failed_proxies)} failed proxies?"):
            for proxy_id in failed_proxies:
                self.poster.remove_proxy(proxy_id)
            self.refresh_proxies()

    def show_proxies_menu(self, event):
        """Show context menu for proxies"""
        # Hide any existing menus first
        self.hide_all_menus()
        
        item = self.proxies_tree.identify_row(event.y)
        if item:
            self.proxies_tree.selection_set(item)
            self.proxies_menu.post(event.x_root, event.y_root)
            self.active_menus.append(self.proxies_menu)
            
            # Auto-hide menu after a delay if no interaction
            self.root.after(5000, lambda: self.safe_hide_menu(self.proxies_menu))



    def check_proxy_with_location(self):
        """Check selected proxy and display location information"""
        selection = self.proxies_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a proxy to check")
            return
        
        item = selection[0]
        proxy_url = self.proxies_tree.item(item)['values'][0]
        
        # Find the proxy by URL
        proxy = None
        for pid, p in self.poster.proxies.items():
            if p.url == proxy_url:
                proxy = p
                break
        
        if not proxy:
            messagebox.showerror("Error", "Proxy not found")
            return
        
        # Create progress dialog
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Checking Proxy")
        progress_dialog.geometry("300x120")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        progress_dialog.resizable(False, False)
        
        # Center the dialog
        progress_dialog.update_idletasks()
        x = (progress_dialog.winfo_screenwidth() // 2) - (progress_dialog.winfo_width() // 2)
        y = (progress_dialog.winfo_screenheight() // 2) - (progress_dialog.winfo_height() // 2)
        progress_dialog.geometry(f"+{x}+{y}")
        
        # Progress content
        ttk.Label(progress_dialog, text=f"Checking proxy: {proxy_url}", font=("Arial", 10, "bold")).pack(pady=10)
        
        progress_bar = ttk.Progressbar(progress_dialog, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        progress_bar.start(10)
        
        status_label = ttk.Label(progress_dialog, text="Testing connection...", foreground="blue")
        status_label.pack(pady=5)
        
        def check_thread():
            try:
                # Update status
                self.root.after(0, lambda: status_label.config(text="Connecting to proxy..."))
                
                # Test proxy and get location
                result = self._test_proxy_with_location(proxy)
                
                # Stop progress bar and close dialog
                self.root.after(0, lambda: [progress_bar.stop(), progress_dialog.destroy()])
                
                if result['working']:
                    message = f"✅ Proxy is WORKING\n\n"
                    message += f"IP Address: {result['ip']}\n"
                    message += f"City: {result['city']}\n"
                    message += f"Region: {result['region']}\n"
                    message += f"Country: {result['country']}\n"
                    message += f"ISP: {result['isp']}\n"
                    
                    self.root.after(0, lambda: messagebox.showinfo("Proxy Check Result", message))
                else:
                    message = f"❌ Proxy is NOT WORKING\n\nError: {result['error']}"
                    self.root.after(0, lambda: messagebox.showerror("Proxy Check Result", message))
                
                # Refresh the proxy list to update status
                self.root.after(0, self.refresh_proxies)
                
            except Exception as e:
                # Stop progress bar and close dialog
                self.root.after(0, lambda: [progress_bar.stop(), progress_dialog.destroy()])
                error_msg = str(e)  # Capture the error message
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error checking proxy: {error_msg}"))
        
        threading.Thread(target=check_thread, daemon=True).start()

    def _test_proxy_with_location(self, proxy):
        """Test proxy and get location information"""
        result = {
            'working': False,
            'ip': None,
            'city': 'Unknown',
            'region': 'Unknown', 
            'country': 'Unknown',
            'isp': 'Unknown',
            'error': None
        }
        
        try:
            # Format proxy for requests
            if proxy.username and proxy.password:
                proxy_url = f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            else:
                proxy_url = f"{proxy.protocol}://{proxy.host}:{proxy.port}"
            
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            # Test IP services in order
            ip_services = [
                "https://api.ipify.org?format=json",
                "https://ifconfig.me/ip", 
                "https://ipinfo.io/ip",
                "https://ident.me"
            ]
            
            ip_address = None
            for service in ip_services:
                try:
                    response = requests.get(service, proxies=proxies, timeout=10)
                    if response.status_code == 200:
                        text = response.text.strip()
                        
                        # Handle JSON response from ipify
                        if text.startswith("{"):
                            ip_address = response.json().get("ip")
                        else:
                            ip_address = text
                        
                        if ip_address:
                            break
                            
                except Exception as e:
                    continue
            
            if not ip_address:
                result['error'] = "Could not get IP address from any service"
                return result
            
            result['ip'] = ip_address
            result['working'] = True
            
            # Get geolocation information
            try:
                geo_url = f"https://ipwho.is/{ip_address}"
                geo_response = requests.get(geo_url, proxies=proxies, timeout=10)
                
                if geo_response.status_code == 200:
                    geo_data = geo_response.json()
                    result['city'] = geo_data.get('city', 'Unknown')
                    result['region'] = geo_data.get('region', 'Unknown')
                    result['country'] = geo_data.get('country', 'Unknown')
                    result['isp'] = geo_data.get('connection', {}).get('isp', 'Unknown')
                    
            except Exception as e:
                # Geolocation failed but proxy is still working
                result['error'] = f"Geolocation lookup failed: {e}"
            
            # Update proxy status and location
            proxy.success_count += 1
            proxy.status = "active"
            
            # Store location information
            if result['city'] != 'Unknown' and result['country'] != 'Unknown':
                proxy.location = f"{result['city']}, {result['country']}"
            
            # Save proxy data
            self.poster._save_proxies()
            
        except Exception as e:
            result['error'] = str(e)
            proxy.failure_count += 1
            if proxy.failure_count >= self.poster.config.get("proxy_max_failures", 3):
                proxy.status = "failed"
            
            # Save proxy data
            self.poster._save_proxies()
        
        return result

    def refresh_proxies(self):
        """Refresh proxies list"""
        # Clear existing items
        for item in self.proxies_tree.get_children():
            self.proxies_tree.delete(item)
        
        # Add proxies
        for proxy_data in self.poster.get_proxy_list():
            last_used = proxy_data['last_used'].strftime("%Y-%m-%d %H:%M") if proxy_data['last_used'] else "Never"
            has_rotation = "Yes" if proxy_data['has_rotation_url'] else "No"
            self.proxies_tree.insert("", tk.END, values=(
                proxy_data['url'],
                has_rotation,
                proxy_data['protocol'],
                proxy_data['status'],
                proxy_data['location'],
                proxy_data['success_count'],
                proxy_data['failure_count'],
                last_used
            ))



def main():
    root = tk.Tk()
    app = RedditPosterGUI(root)
    
    # Handle application close
    def on_closing():
        # Close manual session if active
        app.close_manual_session()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Refresh data periodically
    def periodic_refresh():
        app.refresh_posts()
        app.refresh_proxies()
        
        # Refresh scheduler status if running
        if hasattr(app, 'scheduler_running') and app.scheduler_running:
            try:
                app.update_scheduler_status()
            except:
                pass
        
        root.after(30000, periodic_refresh)  # Refresh every 30 seconds
    
    root.after(1000, periodic_refresh)
    root.mainloop()

if __name__ == "__main__":
    main()