# Reddit Poster Bot

A sophisticated Reddit posting bot with stealth capabilities, multi-account support, and scheduling features. Built with advanced anti-detection measures to avoid Reddit's bot detection systems.

## Features

- **Multi-Account Support**: Manage multiple Reddit accounts
- **Rotating Proxy Support**: Use multiple proxies for enhanced anonymity
- **Stealth Measures**: Advanced anti-detection techniques
- **Post Scheduling**: Schedule posts for optimal timing
- **Multiple Post Types**: Support for text and image posts
- **GUI Interface**: User-friendly graphical interface
- **Command Line Tools**: Powerful CLI for automation
- **Batch Processing**: Import posts from CSV files
- **Account Management**: Test and monitor account status
- **Proxy Management**: Add, test, and rotate proxies automatically
- **Detailed Logging**: Comprehensive logging and statistics

## Installation

1. **Clone or download the files to the `redpost` folder**

2. **Install dependencies**:
   ```bash
   cd redpost
   python setup.py
   ```

3. **Manual dependency installation** (if setup.py fails):
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

### Using the GUI (Recommended)

1. **Start the GUI**:
   ```bash
   python reddit_poster_gui.py
   ```

2. **Add Reddit accounts**:
   - Go to the "Accounts" tab
   - Enter a username and click "Add Account"
   - A browser window will open - login manually
   - Press Enter in the terminal after successful login

3. **Create posts**:
   - Go to the "Posts" tab
   - Fill in the post details
   - Select an account
   - Click "Add Post"

4. **Start posting**:
   - Go to the "Scheduler" tab
   - Click "Start Scheduler"

### Using Command Line

1. **Add an account**:
   ```bash
   python reddit_poster.py
   # Choose option 1 and follow prompts
   ```

2. **Add a post**:
   ```bash
   python reddit_poster.py
   # Choose option 2 and fill in details
   ```

3. **Start scheduler**:
   ```bash
   python reddit_poster.py
   # Choose option 3
   ```

## Advanced Usage

### Command Line Manager

The `reddit_manager.py` script provides powerful command-line tools:

```bash
# Account Management
python reddit_manager.py accounts
python reddit_manager.py test my_username

# Post Management
python reddit_manager.py posts
python reddit_manager.py posts --status pending
python reddit_manager.py batch sample_posts.csv
python reddit_manager.py export my_posts.csv
python reddit_manager.py schedule --interval 60

# Proxy Management
python reddit_manager.py proxies
python reddit_manager.py add-proxy 192.168.1.100 8080 --username user --password pass
python reddit_manager.py import-proxies sample_proxies.txt
python reddit_manager.py test-proxies

# Statistics and Control
python reddit_manager.py stats
python reddit_manager.py run
```

### Batch Posting with CSV

Create a CSV file with the following columns:
- `subreddit`: Target subreddit name
- `title`: Post title
- `content`: Post content (text or image path)
- `post_type`: "text" or "image"
- `nsfw`: "true" or "false"
- `account_name`: Reddit account username
- `scheduled_time`: ISO format datetime (optional)

Example CSV:
```csv
subreddit,title,content,post_type,nsfw,account_name,scheduled_time
funny,My funny post,This is hilarious content,text,false,my_account,2024-12-01 12:00
pics,Cool photo,/path/to/image.jpg,image,false,my_account,2024-12-01 14:00
```

### Proxy Management

#### Adding Proxies

**GUI Method**: Use the Proxies tab to add rotating proxy URLs or static proxies

**Command Line**: 
```bash
# Add a rotating proxy URL
python reddit_manager.py add-proxy http://rotating-proxy.example.com:8080

# Add rotating proxy with authentication
python reddit_manager.py add-proxy http://api.proxyservice.com/rotate --username myuser --password mypass

# Add static proxy (legacy)
python reddit_manager.py add-proxy 192.168.1.100 8080 --username myuser --password mypass --protocol http

# Import from file
python reddit_manager.py import-proxies my_proxies.txt
```

#### Proxy File Format

Create a text file with proxies in these formats:

**Rotating Proxy URLs (Recommended):**
```
# Full rotating proxy URLs
http://rotating-proxy.example.com:8080
https://api.smartproxy.com/v1/rotating
http://username:password@rotating.proxy.service.com:8080
```

**Static Proxies (Legacy):**
```
# Basic format
192.168.1.100:8080

# With protocol
http://192.168.1.100:8080
https://192.168.1.100:8080
socks4://192.168.1.100:1080
socks5://192.168.1.100:1080

# With authentication
username:password@192.168.1.100:8080
http://username:password@192.168.1.100:8080
```

#### Proxy Types and Benefits

**HTTP/HTTPS Proxies:**
- Standard web proxies
- Good for basic anonymity
- Widely supported

**SOCKS4/SOCKS5 Proxies:**
- More secure and versatile
- SOCKS5 supports authentication
- Better for advanced anonymity
- Can handle UDP traffic
- Lower level protocol, harder to detect

**Recommended:** Use SOCKS5 proxies for better anonymity and security.

#### Proxy Testing

The bot automatically tests proxies and marks failed ones. You can also manually test:

```bash
# Test all proxies
python reddit_manager.py test-proxies

# View proxy status
python reddit_manager.py proxies
```

## Configuration

### Selector Configuration System

The bot uses a simple configuration file for all selectors, timeouts, and delays. This makes it easy to adapt to Reddit's UI changes by just editing the JSON file.

#### Configuration Files

- **`selectors_config.json`**: Main configuration file with all selectors and settings
- **`selector_config.py`**: Configuration loader class

#### Updating Configuration

Simply edit the `selectors_config.json` file to update selectors when Reddit changes their UI. The bot will automatically use the new selectors on restart.

#### Configuration Structure

The `selectors_config.json` file contains:

- **reddit_selectors**: All CSS selectors for Reddit elements
  - `title_input`: Selectors for title input fields
  - `text_body`: Selectors for text content areas
  - `upload_buttons`: Selectors for file upload buttons
  - `file_inputs`: Selectors for file input elements
  - `submit_buttons`: Selectors for submit buttons
  - `nsfw_checkbox`: Selectors for NSFW checkboxes
  - `success_indicators`: Selectors for upload success indicators

- **timeouts**: Timeout values in milliseconds
  - `page_load`: Page loading timeout
  - `element_wait`: Element waiting timeout
  - `file_chooser_wait`: File chooser dialog timeout

- **delays**: Delay ranges in seconds
  - `typing_min/max`: Typing speed delays
  - `scroll_min/max`: Scrolling delays
  - `random_min/max`: General random delays

#### Example: Adapting to Reddit Changes

If Reddit changes their upload button, simply edit `selectors_config.json`:

```json
{
  "reddit_selectors": {
    "upload_buttons": [
      "#device-upload-button",
      "button.upload-media",
      "button.new-upload-style"
    ]
  }
}
```

### Settings File

The bot also creates a `data/config.json` file with these settings:

```json
{
  "min_delay_between_posts": 300,
  "max_delay_between_posts": 1800,
  "scroll_delay_min": 2,
  "scroll_delay_max": 8,
  "typing_delay_min": 0.1,
  "typing_delay_max": 0.3,
  "page_load_timeout": 30,
  "max_retries": 3,
  "use_proxies": false,
  "proxy_rotation": true,
  "proxy_test_timeout": 10,
  "proxy_max_failures": 3
}
```

#### Proxy Settings

- `use_proxies`: Enable/disable proxy usage
- `proxy_rotation`: Rotate between available proxies
- `proxy_test_timeout`: Timeout for proxy testing (seconds)
- `proxy_max_failures`: Max failures before marking proxy as failed

### Stealth Features

The bot includes several anti-detection measures:

1. **Random User Agents**: Rotates between different browser user agents
2. **Human-like Behavior**: Random delays, scrolling, and typing patterns
3. **Random Page Visits**: Visits random sites before posting
4. **Cookie Management**: Maintains persistent login sessions
5. **GeoIP Spoofing**: Uses Camoufox for location spoofing
6. **Browser Fingerprinting**: Randomized screen resolutions and settings
7. **Rotating Proxies**: Automatic proxy rotation for IP anonymity
8. **Proxy Health Monitoring**: Automatic testing and failover

## File Structure

```
redpost/
├── reddit_poster.py          # Main bot engine
├── reddit_poster_gui.py      # GUI interface
├── reddit_manager.py         # Command line manager
├── setup.py                  # Setup script
├── launch.py                 # Simple launcher
├── test_installation.py     # Installation test
├── requirements.txt          # Dependencies
├── sample_posts.csv          # Sample CSV template
├── sample_proxies.txt        # Sample proxy file
├── README.md                 # This file
└── data/                     # Data directory
    ├── accounts.json         # Account data
    ├── posts.json           # Posts queue
    ├── proxies.json         # Proxy data
    └── config.json          # Configuration
```

## Account Management

### Adding Accounts

1. **GUI Method**: Use the Accounts tab in the GUI
2. **CLI Method**: Run the main script and choose option 1
3. **Manual Login**: The bot opens a browser for manual login to avoid detection

### Account Status

- **Active**: Account is working and can post
- **Expired**: Login cookies have expired
- **Banned**: Account has been banned or suspended

### Testing Accounts

```bash
python reddit_manager.py test username
```

## Post Management

### Post Types

1. **Text Posts**: Regular text content
2. **Image Posts**: Upload images (JPG, PNG, GIF, WebP)

### Post Status

- **Pending**: Waiting to be posted
- **Posted**: Successfully posted
- **Failed**: Failed to post (check error message)

### Scheduling

Posts can be scheduled for future posting:
- Immediate posting (no schedule)
- Specific date and time
- Batch scheduling with intervals

## Safety and Best Practices

### Account Safety

1. **Use aged accounts**: Older accounts are less likely to be flagged
2. **Vary posting patterns**: Don't post at exact intervals
3. **Monitor account health**: Check for shadowbans regularly
4. **Use quality content**: Avoid spam-like content
5. **Respect rate limits**: Don't post too frequently

### Subreddit Guidelines

1. **Read subreddit rules**: Each subreddit has specific rules
2. **Check karma requirements**: Some subreddits require minimum karma
3. **Avoid banned subreddits**: Don't post to quarantined/banned subs
4. **Use appropriate flairs**: Tag posts correctly

### Technical Safety

1. **Use Proxies**: Enable proxy rotation for IP anonymity
2. **Use VPN**: Consider using a VPN for additional anonymity
3. **Monitor logs**: Check logs for errors or warnings
4. **Test proxies**: Regularly test proxy health
5. **Update regularly**: Keep the bot updated
6. **Backup data**: Regularly backup your accounts, posts, and proxy data

## Troubleshooting

### Common Issues

1. **Login Failed**:
   - Check if account credentials are correct
   - Account might be banned or suspended
   - Try logging in manually first

2. **Post Failed**:
   - Check subreddit rules and requirements
   - Verify account has enough karma
   - Check if content violates Reddit policies

3. **Browser Issues**:
   - Update Camoufox: `pip install --upgrade camoufox`
   - Check if browser dependencies are installed
   - Try running in non-headless mode for debugging

4. **Permission Errors**:
   - Check file permissions in data directory
   - Run with appropriate user permissions

### Debug Mode

To run in debug mode with visible browser:
1. Edit `data/config.json`
2. Set `"headless": false`
3. Restart the bot

### Logs

Check the following log files:
- `reddit_poster.log`: Main bot logs
- Console output: Real-time status updates

## Legal and Ethical Considerations

### Terms of Service

- This bot interacts with Reddit's website
- Users are responsible for complying with Reddit's Terms of Service
- Automated posting may violate Reddit's policies
- Use at your own risk

### Ethical Usage

- Don't spam or post low-quality content
- Respect community guidelines
- Don't manipulate votes or engagement
- Use for legitimate content sharing only

### Disclaimer

This software is provided for educational purposes only. The authors are not responsible for any misuse or violations of Reddit's Terms of Service. Users should ensure their usage complies with all applicable laws and platform policies.

## Support and Contributing

### Getting Help

1. Check this README for common solutions
2. Review the log files for error messages
3. Test with a single account first
4. Verify your Reddit accounts work manually

### Contributing

Contributions are welcome! Please:
1. Test your changes thoroughly
2. Follow the existing code style
3. Update documentation as needed
4. Consider security implications

## Version History

- **v1.0**: Initial release with basic posting functionality
- **v1.1**: Added GUI interface and batch processing
- **v1.2**: Enhanced stealth measures and account management
- **v1.3**: Added scheduling and command-line tools

## License

This project is provided as-is for educational purposes. Use responsibly and in accordance with Reddit's Terms of Service and applicable laws.