// Document Upload Manager with Drag & Drop and Stage-based Progress
(function () {
  document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('upload-file-input');
    const progressModal = document.getElementById('upload-progress-modal');
    const stageText = document.getElementById('upload-stage-text');
    const progressBar = document.getElementById('upload-progress-bar');
    const uploadErrorBox = document.getElementById('upload-error-box');

    if (!dropzone || !fileInput) return;

    // Drag & Drop visual feedback
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('drag-active');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('drag-active');
      }, false);
    });

    // Handle Drop
    dropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        handleFileUpload(files[0]);
      }
    });

    // Handle Click to Browse
    dropzone.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
      }
    });

    function setStage(text, percent) {
      if (stageText) stageText.innerText = text;
      if (progressBar) progressBar.style.width = `${percent}%`;
    }

    async function handleFileUpload(file) {
      if (!file) return;

      const allowedExts = ['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'];
      const ext = file.name.split('.').pop().toLowerCase();
      if (!allowedExts.includes(ext)) {
        AIDoc.showToast("That file type isn't supported. Please upload PDF, DOCX, TXT, JPG, or PNG.", "error");
        return;
      }

      if (file.size > 16 * 1024 * 1024) {
        AIDoc.showToast("Your file exceeds the maximum allowed size of 16MB.", "error");
        return;
      }

      if (file.size === 0) {
        AIDoc.showToast("Uploaded file is empty (0 bytes).", "error");
        return;
      }

      // Open progress modal if available
      if (progressModal) {
        AIDoc.openModal('upload-progress-modal');
        if (uploadErrorBox) uploadErrorBox.style.display = 'none';
        setStage("Uploading document...", 25);
      }

      const formData = new FormData();
      formData.append('file', file);

      // Advance stage timer to reflect pipeline progress
      let stageTimer1 = setTimeout(() => setStage("Extracting text and running OCR...", 50), 800);
      let stageTimer2 = setTimeout(() => setStage("Analyzing document intelligence with AI...", 75), 1800);

      try {
        const response = await fetch('/api/documents/upload', {
          method: 'POST',
          body: formData,
          headers: {
            'Accept': 'application/json'
          }
        });

        clearTimeout(stageTimer1);
        clearTimeout(stageTimer2);

        let data;
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          data = await response.json();
        } else {
          const errText = await response.text();
          console.error("Server returned non-JSON response:", errText.substring(0, 500));
          throw new Error("Server returned an invalid response. Please try again or check server logs.");
        }

        if (response.status === 401) {
          AIDoc.closeModal('upload-progress-modal');
          AIDoc.showToast("You need to sign in to analyze documents.", "warning");
          setTimeout(() => {
            window.location.href = '/login?next=/dashboard';
          }, 1200);
          return;
        }

        if (!response.ok || !data.success) {
          const errMsg = data.error ? data.error.message : "Upload or analysis failed.";
          setStage("Analysis failed", 100);
          if (uploadErrorBox) {
            uploadErrorBox.innerText = errMsg;
            uploadErrorBox.style.display = 'block';
          }
          AIDoc.showToast(errMsg, "error");
          return;
        }

        setStage("Analysis complete! Opening dashboard...", 100);
        AIDoc.showToast("Document analyzed successfully!", "success");

        const redirectUrl = data.data && data.data.redirect_url ? data.data.redirect_url : `/document/${data.data.document_id}`;
        setTimeout(() => {
          window.location.href = redirectUrl;
        }, 800);

      } catch (err) {
        clearTimeout(stageTimer1);
        clearTimeout(stageTimer2);
        console.error("Upload error:", err);
        const netErr = err.message.includes("Server returned") ? err.message : "Network error while processing document. Please check your connection and try again.";
        if (uploadErrorBox) {
          uploadErrorBox.innerText = netErr;
          uploadErrorBox.style.display = 'block';
        }
        AIDoc.showToast(netErr, "error");
      }
    }
  });
})();
