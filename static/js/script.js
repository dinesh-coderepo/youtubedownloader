document.addEventListener('DOMContentLoaded', function() {
    // Initialize elements
    const urlForm = document.getElementById('urlForm');
    const downloadForm = document.getElementById('downloadForm');
    const videoInfo = document.getElementById('videoInfo');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const statusMessage = document.getElementById('statusMessage');
    const downloadButton = document.getElementById('downloadButton');
    let downloadInterval = null;
    
    // Initialize sidebar navigation
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    const contentSections = document.querySelectorAll('.content-section');
    
    // Function to navigate between sections
    function navigateTo(sectionId) {
        // Hide all content sections
        contentSections.forEach(section => {
            section.classList.remove('active');
        });
        
        // Show the selected section
        const targetSection = document.getElementById(sectionId + 'Section');
        if (targetSection) {
            targetSection.classList.add('active');
        }
        
        // Update nav highlighting
        navItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('data-nav') === sectionId) {
                item.classList.add('active');
            }
        });
        
        // Update header title
        const mainHeader = document.querySelector('.main-header h1');
        if (mainHeader) {
            switch(sectionId) {
                case 'downloader':
                    mainHeader.innerHTML = 'YouTube Video Downloader';
                    break;
                case 'library':
                    mainHeader.innerHTML = 'Your Download Library';
                    break;
                case 'help':
                    mainHeader.innerHTML = 'Help & Support';
                    break;
                default:
                    mainHeader.innerHTML = 'DY Downloader';
            }
        }
        
        // Special handling for Library section
        if (sectionId === 'library') {
            loadLibrary();
        }
    }
    
    // Attach click event to navigation items
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const navType = this.getAttribute('data-nav');
            if (navType) {
                navigateTo(navType);
            }
        });
    });
    
    // Function to load library data
    function loadLibrary() {
        const downloadHistory = document.getElementById('downloadHistory');
        
        // Try to load history from localStorage
        let history = [];
        try {
            const savedHistory = localStorage.getItem('downloadHistory');
            if (savedHistory) {
                history = JSON.parse(savedHistory);
            }
        } catch (err) {
            console.error('Error loading history:', err);
        }
        
        // Clear current content
        downloadHistory.innerHTML = '';
        
        // Check if history exists
        if (history && history.length > 0) {
            // Sort by date (newest first)
            history.sort((a, b) => new Date(b.date) - new Date(a.date));
            
            // Create history items
            history.forEach(item => {
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';
                historyItem.innerHTML = `
                    <div class="history-thumb">
                        <img src="${item.thumbnail}" alt="${item.title}">
                    </div>
                    <div class="history-details">
                        <h3 class="history-title">${item.title}</h3>
                        <div class="history-meta">
                            <span>${item.format}</span>
                            <span>${new Date(item.date).toLocaleDateString()}</span>
                        </div>
                    </div>
                `;
                
                // Add click handler to re-download
                historyItem.addEventListener('click', () => {
                    // Navigate to downloader
                    navigateTo('downloader');
                    
                    // Fill in the URL
                    const urlInput = document.getElementById('videoUrl');
                    if (urlInput) {
                        urlInput.value = item.url;
                        
                        // Trigger form submit to fetch video info
                        const urlForm = document.getElementById('urlForm');
                        if (urlForm) {
                            urlForm.dispatchEvent(new Event('submit'));
                        }
                    }
                });
                
                downloadHistory.appendChild(historyItem);
            });
        } else {
            // No history available
            downloadHistory.innerHTML = `
                <div class="text-center text-secondary w-100 py-5">
                    <i class="bi bi-collection-play" style="font-size: 48px;"></i>
                    <p class="mt-3">Your download history will appear here</p>
                </div>
            `;
        }
    }
    
    // Function to save a download to history
    function saveToHistory(videoInfo, format) {
        // Try to load existing history
        let history = [];
        try {
            const savedHistory = localStorage.getItem('downloadHistory');
            if (savedHistory) {
                history = JSON.parse(savedHistory);
            }
        } catch (err) {
            console.error('Error loading history:', err);
        }
        
        // Add new entry
        const newEntry = {
            url: videoInfo.url,
            title: videoInfo.title,
            thumbnail: videoInfo.thumbnail_url,
            format: format,
            date: new Date().toISOString()
        };
        
        // Add to beginning of array
        history.unshift(newEntry);
        
        // Limit history size (keep last 50 entries)
        if (history.length > 50) {
            history = history.slice(0, 50);
        }
        
        // Save back to localStorage
        try {
            localStorage.setItem('downloadHistory', JSON.stringify(history));
        } catch (err) {
            console.error('Error saving history:', err);
        }
    }
    
    // Add typewriter effect to input placeholder
    const videoUrlInput = document.getElementById('videoUrl');
    const placeholders = [
        'Enter YouTube video URL',
        'Paste YouTube link here...',
        'Try https://www.youtube.com/watch?v=l7kQNwJ4H_w'
    ];
    initPlaceholderAnimation(videoUrlInput, placeholders);
    
    // Handle URL form submission
    urlForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Add loading animation
        showLoadingAnimation();
        
        // Reset the UI
        videoInfo.style.display = 'none';
        progressContainer.style.display = 'none';
        statusMessage.innerHTML = '<i class="bi bi-hourglass-split"></i> Fetching video information...';
        statusMessage.classList.add('animate__animated', 'animate__fadeIn');
        statusMessage.style.display = 'block';
        
        const url = videoUrlInput.value.trim();
        
        // Create form data
        const formData = new FormData();
        formData.append('url', url);
        
        // Fetch video info
        fetch('/get_video_info', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Hide status message
            statusMessage.style.display = 'none';
            
            // Display video info with animation
            const thumbnailImg = document.getElementById('videoThumbnail');
            thumbnailImg.src = data.thumbnail_url;
            
            document.getElementById('videoTitle').textContent = data.title;
            document.getElementById('videoAuthor').textContent = data.author;
            
            // Populate resolution dropdown with animation
            populateResolutionOptions(data.streams);
            
            // Store URL in hidden field for download form
            document.getElementById('downloadUrl').value = url;
            
            // Show video info section with animation
            videoInfo.classList.add('animate__animated', 'animate__fadeIn');
            videoInfo.style.display = 'block';
            
            // Stop loading animation
            hideLoadingAnimation();
        })
        .catch(error => {
            statusMessage.innerHTML = `<i class="bi bi-exclamation-triangle"></i> Error: ${error.message}`;
            statusMessage.style.display = 'block';
            console.error('Error:', error);
            hideLoadingAnimation();
        });
    });
    
    // Handle download form submission
    downloadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Add pulse effect to download button
        downloadButton.classList.add('animate__animated', 'animate__pulse');
        
        // Reset the progress
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        progressContainer.style.display = 'block';
        statusMessage.innerHTML = '<i class="bi bi-arrow-down-circle"></i> Starting download...';
        statusMessage.style.display = 'block';
        
        // Disable download button while downloading, but keep it visible with visual indicator
        downloadButton.disabled = true;
        downloadButton.style.display = 'block'; // Ensure button is always visible
        downloadButton.style.opacity = '0.8';   // Slightly dimmed when disabled
        downloadButton.classList.add('position-relative', 'disabled-but-visible');
        
        // Force button visibility with CSS override
        if (!document.getElementById('force-button-visibility')) {
            const styleSheet = document.createElement("style");
            styleSheet.id = 'force-button-visibility';
            styleSheet.textContent = `
                .disabled-but-visible {
                    display: block !important;
                    visibility: visible !important;
                    opacity: 0.8 !important;
                    pointer-events: none;
                    position: relative !important;
                    z-index: 9999 !important;
                }
                #downloadButton {
                    display: block !important;
                    visibility: visible !important;
                }
                #downloadButton::after {
                    content: 'Processing...';
                    position: absolute;
                    bottom: -25px;
                    left: 50%;
                    transform: translateX(-50%);
                    font-size: 0.8rem;
                    color: rgba(255, 255, 255, 0.8);
                    white-space: nowrap;
                }
            `;
            document.head.appendChild(styleSheet);
        }
        
        // Add message beneath the button
        const buttonContainer = downloadButton.closest('form');
        if (buttonContainer && !document.getElementById('buttonMsg')) {
            const buttonMsg = document.createElement('div');
            buttonMsg.id = 'buttonMsg';
            buttonMsg.className = 'text-center text-info small mt-4';
            buttonMsg.innerHTML = '(Button will re-enable when download completes)';
            buttonContainer.appendChild(buttonMsg);
        }
        
        const url = document.getElementById('downloadUrl').value;
        const formatId = document.getElementById('resolutionSelect').value;
        const saveLocation = document.getElementById('saveLocation').value;
        
        // Get custom location if selected
        let customLocation = '';
        if (saveLocation === 'custom') {
            customLocation = document.getElementById('customLocation').value;
            if (!customLocation) {
                statusMessage.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Please enter a custom save location';
                downloadButton.disabled = false;
                return;
            }
        }
        
        // Create form data
        const formData = new FormData();
        formData.append('url', url);
        formData.append('format_id', formatId);
        formData.append('save_location', saveLocation);
        
        // Add custom location if specified
        if (customLocation) {
            formData.append('custom_location', customLocation);
        }
        
        // Start the download
        fetch('/download', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            const downloadId = data.download_id;
            
            // Clear any existing interval
            if (downloadInterval) {
                clearInterval(downloadInterval);
            }
            
            // Start progress checking immediately
            checkProgress(downloadId, url, formatId);
            
            // Check progress periodically - more frequently at the beginning, less often later
            let checkCount = 0;
            downloadInterval = setInterval(() => {
                checkProgress(downloadId, url, formatId);
                
                // After 20 checks (about 5 seconds), slow down the polling rate
                // to reduce server load while still maintaining responsiveness
                checkCount++;
                if (checkCount === 20) {
                    clearInterval(downloadInterval);
                    downloadInterval = setInterval(() => {
                        checkProgress(downloadId, url, formatId);
                    }, 1000); // Switch to checking once per second
                }
            }, 250); // Start with checking 4 times per second
        })
        .catch(error => {
            statusMessage.innerHTML = `<i class="bi bi-exclamation-triangle"></i> Error: ${error.message}`;
            statusMessage.style.display = 'block';
            downloadButton.disabled = false;
            console.error('Error:', error);
        });
    });
    
    // Function to check download progress
    function checkProgress(downloadId, url, formatId) {
        fetch(`/download_progress/${downloadId}`)
        .then(response => response.json())
        .then(data => {
            // Get current progress value shown in the UI
            const currentProgress = parseInt(progressText.textContent) || 0;
            const newProgress = Math.round(data.progress);
            
            // Only update if progress has increased or if status is completed
            if (newProgress > currentProgress || data.status === 'completed') {
                // Animate progress bar
                animateProgressBar(newProgress);
                
                // If progress is complete but status isn't, make sure UI shows 100%
                if (newProgress >= 100 && data.status === 'completed') {
                    animateProgressBar(100);
                }
            }
            
            if (data.status === 'completed' || data.status === 'completed_fallback') {
                clearInterval(downloadInterval);
                
                // Direct download link to local computer
                const directDownloadLink = `/get_file/${downloadId}?url=${encodeURIComponent(url)}&format_id=${formatId}`;
                
                // Different messages based on status
                if (data.status === 'completed_fallback') {
                    statusMessage.innerHTML = '<i class="bi bi-check-circle"></i> Download completed with fallback! <a id="downloadLink" href="#" class="highlight-text">Click here to save</a>';
                } else {
                    statusMessage.innerHTML = '<i class="bi bi-check-circle"></i> Download completed! <a id="downloadLink" href="#" class="highlight-text">Click here to save</a>';
                }
                
                // Create the download link
                const downloadLink = document.getElementById('downloadLink');
                downloadLink.href = directDownloadLink;
                
                // Re-enable download button
                downloadButton.disabled = false;
                downloadButton.classList.remove('disabled-but-visible');
                downloadButton.style.opacity = '1';
                
                // Remove the processing message
                const buttonMsg = document.getElementById('buttonMsg');
                if (buttonMsg) {
                    buttonMsg.remove();
                }
                
                // Get format name from select element
                const formatSelect = document.getElementById('resolutionSelect');
                let formatName = "";
                if (formatSelect && formatSelect.selectedIndex >= 0) {
                    formatName = formatSelect.options[formatSelect.selectedIndex].text;
                }
                
                // Get video info to save in history
                const videoTitle = document.getElementById('videoTitle').textContent;
                const thumbnailUrl = document.getElementById('videoThumbnail').src;
                
                // Save to download history
                saveToHistory({
                    url: url,
                    title: videoTitle,
                    thumbnail_url: thumbnailUrl
                }, formatName);
                
                // Show success animation
                showSuccessAnimation();
                downloadLink.setAttribute('download', ''); // Force download attribute
                downloadLink.classList.add('animate__animated', 'animate__pulse', 'animate__infinite');
                
                // Auto-initiate download to local computer
                setTimeout(() => {
                    window.location.href = directDownloadLink;
                }, 500);
                
                // Re-enable download button
                downloadButton.disabled = false;
                
                // Add success animation
                showSuccessAnimation();
            } else if (data.status.startsWith('error')) {
                clearInterval(downloadInterval);
                statusMessage.innerHTML = `<i class="bi bi-exclamation-triangle"></i> Error: ${data.status.substring(7)}`;
                
                // Re-enable download button on error
                downloadButton.disabled = false;
            } else {
                // Show more granular status messages based on progress
                if (newProgress < 10) {
                    statusMessage.innerHTML = '<i class="bi bi-cloud-download"></i> Starting download...';
                } else if (newProgress < 50) {
                    statusMessage.innerHTML = '<i class="bi bi-cloud-download"></i> Downloading...';
                } else if (newProgress < 90) {
                    statusMessage.innerHTML = '<i class="bi bi-cloud-download"></i> Almost there...';
                } else if (newProgress < 100) {
                    statusMessage.innerHTML = '<i class="bi bi-cloud-download"></i> Finalizing download...';
                }
            }
        })
        .catch(error => {
            // Don't immediately clear interval or show error on first failure
            // Only show error after multiple consecutive failures
            console.error('Error:', error);
            
            // Continue checking, backend might just be busy
            // clearInterval will happen if error persists in the interval function
        });
    }
    
    // Function to animate progress bar
    function animateProgressBar(progress) {
        // Ensure progress is a number and clamp between 0-100
        progress = Math.min(Math.max(parseInt(progress) || 0, 0), 100);
        
        // Force browser to recognize style changes by using setTimeout
        setTimeout(() => {
            progressBar.style.width = `${progress}%`;
            progressText.textContent = `${progress}%`;
            
            // Force the browser to redraw by accessing a layout property
            void progressBar.offsetWidth;
            
            // Log to console for debugging
            console.log(`Setting progress bar to ${progress}%`);
            
            // Add pulse effect at certain milestones or on any change
            if (progress > 0 && progress % 10 === 0) {
                progressBar.classList.add('animate__animated', 'animate__flash');
                setTimeout(() => {
                    progressBar.classList.remove('animate__animated', 'animate__flash');
                }, 300);
            }
        }, 0);
    }
    
    // Function to populate resolution options
    function populateResolutionOptions(streams) {
        const resolutionSelect = document.getElementById('resolutionSelect');
        resolutionSelect.innerHTML = ''; // Clear existing options
        
        streams.forEach((stream, index) => {
            const option = document.createElement('option');
            option.value = stream.format_id; // Use format_id for yt-dlp
            
            // Calculate filesize - use filesize, filesize_approx, or default to 10MB
            const filesize = stream.filesize || stream.filesize_approx || (10 * 1024 * 1024);
            const fileSizeMB = (filesize / (1024 * 1024)).toFixed(2);
            
            // Get extension, default to mp4
            const ext = stream.ext || 'mp4';
            
            // Determine label text based on stream type
            let optionText = '';
            
            if (stream.is_highest) {
                optionText = `${stream.resolution} (${ext}) - Best Quality`;
            } else if (stream.is_best_audio) {
                optionText = `${stream.resolution} (${ext}) - Highest Bitrate`;
            } else if (stream.type === 'audio') {
                optionText = `${stream.resolution} (${ext}) - ${fileSizeMB} MB`;
            } else {
                optionText = `${stream.resolution} (${ext}) - ${fileSizeMB} MB`;
            }
            
            option.textContent = optionText;
            
            // Add a small delay for each option to create a cascade effect
            setTimeout(() => {
                resolutionSelect.appendChild(option);
            }, index * 50);
        });
        
        // Add event listener to resolution select to ensure download button is visible
        resolutionSelect.addEventListener('change', function() {
            // Re-enable and show download button when format changes
            downloadButton.disabled = false;
            downloadButton.style.display = 'block';
        });
    }
    
    // Initialize save location selection
    const saveLocationSelect = document.getElementById('saveLocation');
    const customLocationContainer = document.getElementById('customLocationContainer');
    const customLocationInput = document.getElementById('customLocation');
    
    if (saveLocationSelect) {
        saveLocationSelect.addEventListener('change', function() {
            if (this.value === 'custom') {
                customLocationContainer.classList.remove('d-none');
                customLocationInput.required = true;
            } else {
                customLocationContainer.classList.add('d-none');
                customLocationInput.required = false;
            }
        });
    }
    
    // Function to initialize glow animation (removed as we're using new UI)
    
    // Function to animate input placeholder
    function initPlaceholderAnimation(input, texts) {
        let currentIndex = 0;
        
        setInterval(() => {
            input.setAttribute('placeholder', texts[currentIndex]);
            currentIndex = (currentIndex + 1) % texts.length;
        }, 3000);
    }
    
    // Loading animation
    function showLoadingAnimation() {
        document.body.classList.add('loading');
        
        // Create loading overlay if it doesn't exist
        if (!document.querySelector('.loading-overlay')) {
            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = '<div class="spinner"></div>';
            document.body.appendChild(overlay);
            
            // Animate in
            setTimeout(() => {
                overlay.style.opacity = '1';
            }, 10);
        }
    }
    
    function hideLoadingAnimation() {
        document.body.classList.remove('loading');
        
        // Remove loading overlay with fade out
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => {
                overlay.remove();
            }, 300);
        }
    }
    
    // Success animation
    function showSuccessAnimation() {
        // Add confetti effect
        for (let i = 0; i < 30; i++) {
            createConfetti();
        }
    }
    
    function createConfetti() {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.style.left = Math.random() * 100 + 'vw';
        confetti.style.animationDuration = (Math.random() * 3 + 2) + 's';
        confetti.style.opacity = Math.random() + 0.5;
        
        // Random colors
        const colors = ['#00b3ff', '#00ff73', '#ff00e6', '#ffbe0b'];
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        
        document.body.appendChild(confetti);
        
        // Remove after animation completes
        setTimeout(() => {
            confetti.remove();
        }, 5000);
    }
    
    // Add CSS for additional animations
    addAnimationStyles();
    
    function addAnimationStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(15, 23, 42, 0.7);
                backdrop-filter: blur(5px);
                z-index: 1000;
                display: flex;
                justify-content: center;
                align-items: center;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .spinner {
                width: 50px;
                height: 50px;
                border: 5px solid rgba(0, 179, 255, 0.3);
                border-radius: 50%;
                border-top-color: var(--glow-color);
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            
            .confetti {
                position: fixed;
                width: 10px;
                height: 10px;
                z-index: 1000;
                top: -10px;
                border-radius: 0;
                animation: fall linear forwards;
            }
            
            @keyframes fall {
                to {
                    transform: translateY(100vh) rotate(720deg);
                }
            }
        `;
        document.head.appendChild(style);
    }
});
