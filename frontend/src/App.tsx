import { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("en");
  const [response, setResponse] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a PDF file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);

    try {
      // Simulated response for demo
      setResponse(JSON.stringify({ 
        success: true, 
        filename: file.name,
        rows: 150,
        message: "File processed successfully" 
      }, null, 2));
      
      // Real API call:
      // const res = await axios.post("http://127.0.0.1:5000/upload", formData, {
      //   headers: { "Content-Type": "multipart/form-data" },
      // });
      // setResponse(JSON.stringify(res.data, null, 2));
    } catch (err: any) {
      console.error(err);
      alert("Upload failed.");
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === "application/pdf") {
      setFile(droppedFile);
    }
  };

  // SVG Icons
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
            <h1 className="title">PDF to CSV Uploader</h1>
            <p className="subtitle">Convert your PDF documents to CSV format</p>
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
                          onClick={(e) => {
                            e.preventDefault();
                            setFile(null);
                          }}
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
              disabled={!file}
              className={`upload-btn ${!file ? 'disabled' : ''}`}
            >
              Upload and Convert
            </button>

            {response && (
              <div className="response-section">
                <h3 className="response-title">Response</h3>
                <pre className="response-content">{response}</pre>
              </div>
            )}
          </div>
        </div>

        <p className="footer-text">Upload your PDF file to convert it to CSV format</p>
      </div>
    </div>
  );
}

export default App;