import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Upload, Image, QrCode, Loader2, X, Check, Copy, ExternalLink } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function EventDetailPage() {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const { getAuthHeaders } = useAuth();
  
  const [event, setEvent] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [qrDialogOpen, setQrDialogOpen] = useState(false);

  const fetchEventData = useCallback(async () => {
    try {
      const [eventRes, photosRes] = await Promise.all([
        axios.get(`${API}/events/${eventId}`, { headers: getAuthHeaders() }),
        axios.get(`${API}/events/${eventId}/photos`, { headers: getAuthHeaders() })
      ]);
      setEvent(eventRes.data);
      setPhotos(photosRes.data);
    } catch (error) {
      toast.error("Failed to load event");
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  }, [eventId, getAuthHeaders, navigate]);

  useEffect(() => {
    fetchEventData();
  }, [fetchEventData]);

  const handleFileUpload = async (files) => {
    if (!files.length) return;
    
    const imageFiles = Array.from(files).filter(f => f.type.startsWith("image/"));
    if (!imageFiles.length) {
      toast.error("Please select image files only");
      return;
    }
    
    setUploading(true);
    setUploadProgress(0);
    
    try {
      const formData = new FormData();
      imageFiles.forEach(file => formData.append("files", file));
      
      const response = await axios.post(
        `${API}/events/${eventId}/photos`,
        formData,
        {
          headers: {
            ...getAuthHeaders(),
            "Content-Type": "multipart/form-data"
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        }
      );
      
      setPhotos([...photos, ...response.data]);
      setEvent({ ...event, photo_count: event.photo_count + response.data.length });
      toast.success(`${response.data.length} photos uploaded successfully!`);
    } catch (error) {
      toast.error("Failed to upload photos");
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const customerUrl = `${window.location.origin}/event/${eventId}`;

  const copyLink = () => {
    navigator.clipboard.writeText(customerUrl);
    toast.success("Link copied to clipboard!");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white/40" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-white/5 bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => navigate("/dashboard")}
              className="text-white/60 hover:text-white hover:bg-white/10"
              data-testid="back-btn"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-lg font-bold text-white truncate max-w-[200px] sm:max-w-none" style={{ fontFamily: 'Manrope' }}>
                {event?.name}
              </h1>
              <p className="text-sm text-white/50">{event?.date}</p>
            </div>
          </div>
          
          <Dialog open={qrDialogOpen} onOpenChange={setQrDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                variant="outline" 
                className="border-white/10 text-white hover:bg-white/10"
                data-testid="show-qr-btn"
              >
                <QrCode className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Share QR</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-white/10 text-white max-w-sm" data-testid="qr-dialog">
              <DialogHeader>
                <DialogTitle className="text-center" style={{ fontFamily: 'Manrope' }}>Share Event</DialogTitle>
              </DialogHeader>
              <div className="flex flex-col items-center py-6">
                <div className="bg-white p-4 rounded-xl mb-4">
                  <QRCodeSVG value={customerUrl} size={180} />
                </div>
                <p className="text-sm text-white/60 text-center mb-4">
                  Guests can scan this QR code to find their photos
                </p>
                <div className="flex gap-2 w-full">
                  <Button 
                    variant="outline" 
                    className="flex-1 border-white/10 text-white hover:bg-white/10"
                    onClick={copyLink}
                    data-testid="copy-link-btn"
                  >
                    <Copy className="w-4 h-4 mr-2" />
                    Copy Link
                  </Button>
                  <Button 
                    variant="outline"
                    className="border-white/10 text-white hover:bg-white/10"
                    onClick={() => window.open(customerUrl, "_blank")}
                    data-testid="open-link-btn"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
          <Card className="bg-card border-white/5">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/5 rounded-lg flex items-center justify-center">
                  <Image className="w-5 h-5 text-white/60" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white" style={{ fontFamily: 'Manrope' }}>{event?.photo_count || 0}</p>
                  <p className="text-xs text-white/50">Photos</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Upload Zone */}
        <Card className="bg-card border-white/5 mb-8" data-testid="upload-zone">
          <CardHeader>
            <CardTitle className="text-lg text-white" style={{ fontFamily: 'Manrope' }}>Bulk Upload</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={`upload-zone ${dragOver ? "drag-over" : ""}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              {uploading ? (
                <div className="space-y-4">
                  <Loader2 className="w-12 h-12 text-white/40 mx-auto animate-spin" />
                  <div className="w-full max-w-xs mx-auto">
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-white transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                    <p className="text-white/60 text-sm mt-2">{uploadProgress}% uploaded</p>
                  </div>
                </div>
              ) : (
                <>
                  <Upload className="w-12 h-12 text-white/30 mx-auto mb-4" />
                  <p className="text-white/60 mb-2">Drag and drop photos here</p>
                  <p className="text-white/40 text-sm mb-4">or</p>
                  <label className="cursor-pointer">
                    <input
                      type="file"
                      multiple
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => handleFileUpload(e.target.files)}
                      data-testid="file-input"
                    />
                    <span className="inline-flex items-center gap-2 px-6 py-2.5 bg-white text-black rounded-full font-medium hover:bg-white/90 transition-colors">
                      <Upload className="w-4 h-4" />
                      Browse Files
                    </span>
                  </label>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Photo Grid */}
        <div>
          <h2 className="text-xl font-bold text-white mb-4" style={{ fontFamily: 'Manrope' }}>
            Event Photos
          </h2>
          
          {photos.length === 0 ? (
            <div className="text-center py-16 bg-card border border-white/5 rounded-xl">
              <Image className="w-16 h-16 text-white/20 mx-auto mb-4" />
              <p className="text-white/50">No photos uploaded yet</p>
              <p className="text-white/30 text-sm mt-1">Upload photos using the form above</p>
            </div>
          ) : (
            <div className="photo-grid">
              <AnimatePresence>
                {photos.map((photo, index) => (
                  <motion.div
                    key={photo.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ delay: index * 0.02 }}
                    className="relative group aspect-square rounded-lg overflow-hidden bg-white/5"
                    data-testid={`photo-${photo.id}`}
                  >
                    <img
                      src={photo.url}
                      alt={photo.filename}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <a 
                        href={photo.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="p-2 bg-white/20 rounded-full hover:bg-white/30 transition-colors"
                      >
                        <ExternalLink className="w-5 h-5 text-white" />
                      </a>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
