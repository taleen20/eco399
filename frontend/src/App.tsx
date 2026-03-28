import { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

type JobState = 'pending' | 'started' | 'progress' | 'success' | 'failure' | '';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("en");
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [jobId, setJobId] = useState("");
  const [jobState, setJobState] = useState<JobState>("");
  const [jobStep, setJobStep] = useState("");
  const [downloadFilename, setDownloadFilename] = useState("");
  const [tablesFound, setTablesFound] = useState<number | null>(null);
  const [ocrFailed, setOcrFailed] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollCountRef = useRef(0);
  const MAX_POLLS = 150; // 5 minutes at 2s intervals

  const notify = (title: string, body: string) => {
    if (Notification.permission === 'granted') {
      new Notification(title, { body });
    }
  };

  useEffect(() => {
    if (!jobId) return;

    pollCountRef.current = 0;
    Notification.requestPermission();

    pollRef.current = setInterval(async () => {
      pollCountRef.current += 1;

      if (pollCountRef.current > MAX_POLLS) {
        setErrorMessage("Processing timed out. The job may still be running — try refreshing.");
        document.title = "⚠ Timed out — Price of Empire";
        clearInterval(pollRef.current!);
        return;
      }

      try {
        const res = await axios.get(`/api/status/${jobId}`);
        const { state, step, filename, tables_found, ocr_failed, error } = res.data;
        setJobState(state);
        setJobStep(step ?? "");

        if (state === 'success') {
          setDownloadFilename(filename);
          setTablesFound(tables_found);
          setOcrFailed(ocr_failed ?? 0);
          document.title = "✓ Done — Price of Empire";
          notify("Conversion complete", tables_found === 0
            ? "No tables were detected in the PDF."
            : `${tables_found} table(s) extracted. Your CSV is ready to download.`
          );
          clearInterval(pollRef.current!);
        } else if (state === 'failure') {
          setErrorMessage(error || "Processing failed.");
          document.title = "⚠ Failed — Price of Empire";
          notify("Conversion failed", error || "Processing failed.");
          clearInterval(pollRef.current!);
        }
      } catch {
        setErrorMessage("Lost connection while polling for status.");
        clearInterval(pollRef.current!);
      }
    }, 2000);

    return () => clearInterval(pollRef.current!);
  }, [jobId]);

  useEffect(() => {
    return () => { document.title = "Price of Empire"; };
  }, []);

  const handleUpload = async () => {
    if (!file) return;

    if (file.size > 50 * 1024 * 1024) {
      setErrorMessage("File exceeds the 50MB limit.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);

    setIsUploading(true);
    setJobId("");
    setJobState("");
    setJobStep("");
    setDownloadFilename("");
    setTablesFound(null);
    setOcrFailed(0);
    setErrorMessage("");

    try {
      const res = await axios.post("/api/upload", formData);
      setJobId(res.data.job_id);
      setJobState("pending");
    } catch (err: any) {
      setErrorMessage(err.response?.data?.error || "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === "application/pdf") setFile(droppedFile);
  };

  const isProcessing = isUploading || (!!jobId && jobState !== 'success' && jobState !== 'failure');

  const buttonLabel = isUploading
    ? "Uploading..."
    : isProcessing
    ? "Processing..."
    : "Upload and Convert";

  const stepLabel: Record<string, string> = {
    pending: "Queued",
    started: "Starting",
    progress: jobStep,
    success: `Done — ${tablesFound} table(s) found`,
    failure: errorMessage,
  };

  const UploadIcon = () => (
    <svg className="icon-upload" viewBox="0 0 120 120" fill="none">
      <path d="M60 15C35.1472 15 15 35.1472 15 60C15 84.8528 35.1472 105 60 105C84.8528 105 105 84.8528 105 60C105 35.1472 84.8528 15 60 15Z"
            fill="#E8F1FF" stroke="#2563EB" strokeWidth="4"/>
      <path d="M60 75V45M60 45L47.5 57.5M60 45L72.5 57.5"
            stroke="#2563EB" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  const CheckIcon = () => (
    <svg className="icon-check" viewBox="0 0 80 80" fill="none">
      <circle cx="40" cy="40" r="35" fill="#10B981" stroke="#059669" strokeWidth="3"/>
      <path d="M25 40L35 50L55 30" stroke="white" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  return (
    <div className="app-container">
      <div className="app-wrapper">
        <div className="card">
          <div className="header">
            <h1 className="title">ECO399: Price of Empire</h1>
          </div>

          <div className="content">
            <div className="form-group">
              <label className="label">Upload PDF File</label>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`upload-area ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
              >
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="file-input"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="upload-label">
                  {file ? (
                    <div>
                      <CheckIcon />
                      <div className="file-info">
                        <p className="file-name">{file.name}</p>
                        <p className="file-size">{(file.size / 1024).toFixed(2)} KB</p>
                        <button
                          type="button"
                          className="change-file-btn"
                          onClick={(e) => { e.preventDefault(); setFile(null); }}
                        >
                          Choose different file
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <UploadIcon />
                      <p className="upload-text">Drop your PDF here or click to browse</p>
                      <p className="upload-subtext">PDF files only</p>
                    </div>
                  )}
                </label>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="language" className="label">Select Language</label>
              <select
                id="language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="select-input"
              >
                <option value="en">English</option>
                <option value="es">Spanish</option>
              </select>
            </div>

            <button
              onClick={handleUpload}
              disabled={!file || isProcessing}
              className={`upload-btn ${!file || isProcessing ? 'disabled' : ''}`}
            >
              {buttonLabel}
            </button>

            {jobState && (
              <p className={`job-status ${jobState}`}>
                {stepLabel[jobState] ?? jobState}
              </p>
            )}

            {jobState === 'success' && tablesFound === 0 && (
              <p className="job-status failure">No tables were detected in this PDF.</p>
            )}

            {jobState === 'success' && ocrFailed > 0 && (
              <p className="job-status failure">
                {ocrFailed} table(s) were detected but could not be read by OCR and are missing from the CSV.
              </p>
            )}

            {downloadFilename && tablesFound !== null && tablesFound > 0 && (
              <a
                href={`/api/download/${downloadFilename}`}
                download={downloadFilename}
                className="download-link"
              >
                Download {downloadFilename}
              </a>
            )}
          </div>
        </div>

        <p className="footer-text">Upload your PDF file to convert it to CSV format</p>
      </div>
    </div>
  );
}

export default App;
