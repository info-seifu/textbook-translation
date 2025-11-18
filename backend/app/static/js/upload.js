// アップロード画面のJavaScript

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const dropZone = document.getElementById('dropZone');
    const pdfFile = document.getElementById('pdfFile');
    const dropZoneContent = document.getElementById('dropZoneContent');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const submitBtn = document.getElementById('submitBtn');
    const progressSection = document.getElementById('progressSection');

    let selectedFile = null;

    // ドロップゾーンクリックでファイル選択
    dropZone.addEventListener('click', () => {
        pdfFile.click();
    });

    // ファイル選択時
    pdfFile.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFile(file);
        }
    });

    // ドラッグ＆ドロップ処理
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drop-zone-active');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drop-zone-active');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drop-zone-active');

        const file = e.dataTransfer.files[0];
        if (file && file.type === 'application/pdf') {
            handleFile(file);
        } else {
            showToast('PDFファイルを選択してください', 'error');
        }
    });

    // ファイル処理
    function handleFile(file) {
        if (file.size > 50 * 1024 * 1024) {
            showToast('ファイルサイズが50MBを超えています', 'error');
            return;
        }

        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);

        dropZoneContent.classList.add('hidden');
        fileInfo.classList.remove('hidden');

        showToast('ファイルが選択されました', 'success');
    }

    // フォーム送信
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // バリデーション
        if (!selectedFile) {
            showToast('PDFファイルを選択してください', 'error');
            return;
        }

        const selectedLanguages = Array.from(
            document.querySelectorAll('input[name="languages"]:checked')
        ).map(cb => cb.value);

        if (selectedLanguages.length === 0) {
            showToast('翻訳先言語を少なくとも1つ選択してください', 'error');
            return;
        }

        const translatorEngine = document.querySelector('input[name="translator_engine"]:checked').value;

        // ローディング表示
        const originalBtnText = submitBtn.innerHTML;
        showLoading(submitBtn);

        try {
            // Step 1: PDFアップロード
            const formData = new FormData();
            formData.append('file', selectedFile);

            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                const error = await uploadResponse.json();
                throw new Error(error.detail || 'アップロードに失敗しました');
            }

            const uploadData = await uploadResponse.json();
            const jobId = uploadData.job_id;

            showToast('アップロード完了。OCR処理を開始しています...', 'success');

            // 進捗表示開始
            progressSection.classList.remove('hidden');
            updateOCRProgress(jobId);

            // Step 2: OCR完了を待つ
            await waitForOCR(jobId);

            showToast('OCR完了。翻訳を開始しています...', 'success');

            // Step 3: バッチ翻訳開始
            const translateData = {
                job_id: jobId,
                target_languages: selectedLanguages.map(lang => ({
                    language: lang,
                    translator_engine: translatorEngine
                })),
                translator_engine: translatorEngine
            };

            const translateResponse = await fetch('/api/batch-translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(translateData)
            });

            if (!translateResponse.ok) {
                const error = await translateResponse.json();
                throw new Error(error.detail || '翻訳開始に失敗しました');
            }

            showToast('翻訳を開始しました', 'success');

            // ステータスページにリダイレクト
            setTimeout(() => {
                window.location.href = `/status/${jobId}`;
            }, 1500);

        } catch (error) {
            console.error('エラー:', error);
            showToast(error.message || '処理に失敗しました', 'error');
            hideLoading(submitBtn, originalBtnText);
            progressSection.classList.add('hidden');
        }
    });

    // OCR進捗更新
    async function updateOCRProgress(jobId) {
        const ocrStatus = document.getElementById('ocrStatus');
        const ocrProgress = document.getElementById('ocrProgress');

        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            const data = await response.json();

            const status = data.job.ocr_status;

            switch (status) {
                case 'pending':
                    ocrStatus.textContent = '待機中...';
                    ocrProgress.style.width = '10%';
                    break;
                case 'processing':
                    ocrStatus.textContent = '処理中...';
                    ocrProgress.style.width = '50%';
                    break;
                case 'completed':
                    ocrStatus.textContent = '完了';
                    ocrProgress.style.width = '100%';
                    return;
                case 'failed':
                    ocrStatus.textContent = 'エラー';
                    ocrProgress.style.width = '0%';
                    throw new Error(data.job.ocr_error || 'OCRに失敗しました');
            }

            // 2秒後に再チェック
            if (status !== 'completed' && status !== 'failed') {
                setTimeout(() => updateOCRProgress(jobId), 2000);
            }
        } catch (error) {
            console.error('進捗取得エラー:', error);
        }
    }

    // OCR完了を待つ
    function waitForOCR(jobId) {
        return new Promise((resolve, reject) => {
            const checkStatus = async () => {
                try {
                    const response = await fetch(`/api/jobs/${jobId}`);
                    const data = await response.json();

                    if (data.job.ocr_status === 'completed') {
                        resolve();
                    } else if (data.job.ocr_status === 'failed') {
                        reject(new Error(data.job.ocr_error || 'OCRに失敗しました'));
                    } else {
                        setTimeout(checkStatus, 3000);
                    }
                } catch (error) {
                    reject(error);
                }
            };

            checkStatus();
        });
    }
});
