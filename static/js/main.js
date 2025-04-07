document.addEventListener('DOMContentLoaded', function() {
    // File upload handling
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const uploadStatus = document.getElementById('uploadStatus');
    const fileList = document.getElementById('fileList');
    
    // Function to clear previous backend data before new upload
    function clearPreviousUploads() {
        fetch('/clear', { method: 'POST' })
            .then(response => {
                console.log('Previous resume data cleared.');
            })
            .catch(error => {
                console.error('Error clearing previous data:', error);
            });
    }
    
    if (dropzone) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, preventDefaults, false);
        });
        
        // Highlight drop area when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, unhighlight, false);
        });
        
        // Handle dropped files
        dropzone.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            clearPreviousUploads();
            updateFileList(files);
            fileInput.files = files;
        }, false);
        
        // Handle click to select files
        dropzone.addEventListener('click', function() {
            fileInput.click();
        });
        
        // Handle file input change
        fileInput.addEventListener('change', function() {
            clearPreviousUploads();
            updateFileList(this.files);
        });
    }
    
    // Job requirements form
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const requiredSkills = document.getElementById('requiredSkills').value.trim();
            if (!requiredSkills) {
                e.preventDefault();
                alert('Please enter at least one required skill');
            }
        });
    }
    
    // Skills input enhancement
    const skillsInput = document.getElementById('requiredSkills');
    if (skillsInput) {
        skillsInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const skills = this.value.split(',');
                if (skills[skills.length - 1].trim() !== '') {
                    this.value += ', ';
                }
            }
        });
    }
    
    // Functions for file upload
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        dropzone.classList.add('border-primary');
        dropzone.classList.add('bg-dark');
    }
    
    function unhighlight() {
        dropzone.classList.remove('border-primary');
        dropzone.classList.remove('bg-dark');
    }
    
    function updateFileList(files) {
        if (!fileList) return;
        
        fileList.innerHTML = '';
        let validFiles = 0;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const fileExt = file.name.split('.').pop().toLowerCase();
            
            if (fileExt === 'pdf') {
                validFiles++;
                const fileItem = document.createElement('div');
                fileItem.className = 'alert alert-info mb-2';
                fileItem.innerHTML = `
                    <i class="fas fa-file-pdf me-2"></i>
                    ${file.name} (${(file.size / 1024).toFixed(1)} KB)
                `;
                fileList.appendChild(fileItem);
            } else {
                const fileItem = document.createElement('div');
                fileItem.className = 'alert alert-danger mb-2';
                fileItem.innerHTML = `
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${file.name} - Invalid file type (Only PDF files are allowed)
                `;
                fileList.appendChild(fileItem);
            }
        }
        
        if (validFiles > 0) {
            uploadStatus.innerHTML = `<div class="alert alert-success">${validFiles} valid PDF file(s) selected</div>`;
            document.getElementById('uploadBtn').disabled = false;
        } else {
            uploadStatus.innerHTML = '<div class="alert alert-warning">No valid PDF files selected</div>';
            document.getElementById('uploadBtn').disabled = true;
        }
    }
    
    // Skills visualization in results
    const skillElements = document.querySelectorAll('.skill-tag');
    if (skillElements.length > 0) {
        skillElements.forEach(element => {
            // Add a small animation when hovering over skills
            element.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.1)';
            });
            
            element.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
    }
});
