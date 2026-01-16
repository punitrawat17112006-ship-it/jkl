import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Camera, Image, Loader2, Download, ChevronLeft, ChevronRight, X, Search, User, Sparkles } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { toast } from "sonner";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function CustomerEventPage() {
  const { eventId } = useParams();
  const [event, setEvent] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [matchedPhotos, setMatchedPhotos] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [showSelfieDialog, setShowSelfieDialog] = useState(false);
  const [selfiePreview, setSelfiePreview] = useState(null);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  useEffect(() => {
    const fetchEventData = async () => {
      try {
        const [eventRes, photosRes] = await Promise.all([
          axios.get(`${API}/public/events/${eventId}`),
          axios.get(`${API}/public/events/${eventId}/photos`)
        ]);
        setEvent(eventRes.data);
        setPhotos(photosRes.data);
      } catch (err) {
        setError("Event not found");
      } finally {
        setLoading(false);
      }
    };
    fetchEventData();
  }, [eventId]);

  const handleSelfieCapture = async (file) => {
    if (!file) return;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setSelfiePreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const handleFindMyPhotos = async () => {
    if (!selfiePreview) {
      toast.error("Please take or upload a selfie first");
      return;
    }

    setSearching(true);
    setShowSelfieDialog(false);

    try {
      // Convert preview to file
      const response = await fetch(selfiePreview);
      const blob = await response.blob();
      const file = new File([blob], "selfie.jpg", { type: "image/jpeg" });

      const formData = new FormData();
      formData.append("selfie", file);

      const result = await axios.post(
        `${API}/public/events/${eventId}/find-my-photos`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      setMatchedPhotos(result.data);
      
      if (result.data.length === 0) {
        toast.info("No matching photos found. Try browsing all photos.");
      } else {
        toast.success(`Found ${result.data.length} photos that might be you!`);
      }
    } catch (err) {
      toast.error("Failed to search photos. Please try again.");
      console.error(err);
    } finally {
      setSearching(false);
      setSelfiePreview(null);
    }
  };

  const clearSearch = () => {
    setMatchedPhotos(null);
  };

  const navigatePhoto = (direction) => {
    const displayPhotos = matchedPhotos || photos;
    const currentIndex = displayPhotos.findIndex(p => p.id === selectedPhoto.id);
    let newIndex = currentIndex + direction;
    if (newIndex < 0) newIndex = displayPhotos.length - 1;
    if (newIndex >= displayPhotos.length) newIndex = 0;
    setSelectedPhoto(displayPhotos[newIndex]);
  };

  const displayPhotos = matchedPhotos || photos;

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white/40" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="bg-card border-white/10 max-w-md w-full">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Camera className="w-8 h-8 text-white/30" />
            </div>
            <h1 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'Manrope' }}>
              Event Not Found
            </h1>
            <p className="text-white/50">This event may have been removed or the link is invalid.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-white/5 bg-card/50 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center">
                <Camera className="w-5 h-5 text-white" strokeWidth={1.5} />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white" style={{ fontFamily: 'Manrope' }}>
                  {event?.name}
                </h1>
                <p className="text-sm text-white/50">{event?.date}</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Find My Photos CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Card className="bg-gradient-to-r from-white/10 to-white/5 border-white/10 overflow-hidden">
            <CardContent className="p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row items-center gap-6">
                <div className="w-20 h-20 bg-white/10 rounded-2xl flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-10 h-10 text-white" />
                </div>
                <div className="text-center sm:text-left flex-1">
                  <h2 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: 'Manrope' }}>
                    Find Your Photos
                  </h2>
                  <p className="text-white/60 mb-4">
                    Take a selfie and we'll use AI to find photos where you appear
                  </p>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <Button
                      onClick={() => setShowSelfieDialog(true)}
                      className="bg-white text-black hover:bg-white/90 rounded-full px-6 font-semibold"
                      disabled={searching}
                      data-testid="find-my-photos-btn"
                    >
                      {searching ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Searching...
                        </>
                      ) : (
                        <>
                          <Search className="w-4 h-4 mr-2" />
                          Find My Photos
                        </>
                      )}
                    </Button>
                    {matchedPhotos && (
                      <Button
                        onClick={clearSearch}
                        variant="outline"
                        className="border-white/20 text-white hover:bg-white/10 rounded-full"
                        data-testid="clear-search-btn"
                      >
                        Show All Photos
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Search Results Info */}
        {matchedPhotos && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-6 flex items-center gap-2 text-white/60"
          >
            <User className="w-4 h-4" />
            <span>Showing {matchedPhotos.length} photos matching your selfie</span>
          </motion.div>
        )}

        {/* Photo Grid */}
        {displayPhotos.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Image className="w-10 h-10 text-white/20" />
            </div>
            <h2 className="text-xl font-semibold text-white/60 mb-2" style={{ fontFamily: 'Manrope' }}>
              {matchedPhotos ? "No matching photos found" : "No photos yet"}
            </h2>
            <p className="text-white/40">
              {matchedPhotos ? "Try browsing all photos instead" : "Photos will appear here once uploaded"}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-4">
            <AnimatePresence>
              {displayPhotos.map((photo, index) => (
                <motion.div
                  key={photo.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ delay: index * 0.02 }}
                  className="relative aspect-square rounded-lg overflow-hidden bg-white/5 cursor-pointer group"
                  onClick={() => setSelectedPhoto(photo)}
                  data-testid={`customer-photo-${photo.id}`}
                >
                  <img
                    src={photo.url.startsWith('http') ? photo.url : `${BACKEND_URL}${photo.url}`}
                    alt={photo.filename}
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    loading="lazy"
                  />
                  {photo.similarity && (
                    <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-sm px-2 py-1 rounded-full text-xs text-white font-medium">
                      {photo.similarity}% match
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="text-white text-sm font-medium">View</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </main>

      {/* Selfie Dialog */}
      <Dialog open={showSelfieDialog} onOpenChange={setShowSelfieDialog}>
        <DialogContent className="bg-card border-white/10 text-white max-w-md" data-testid="selfie-dialog">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-center" style={{ fontFamily: 'Manrope' }}>
              Take a Selfie
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {selfiePreview ? (
              <div className="relative">
                <img 
                  src={selfiePreview} 
                  alt="Selfie preview" 
                  className="w-full aspect-square object-cover rounded-xl"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2 bg-black/50 hover:bg-black/70"
                  onClick={() => setSelfiePreview(null)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ) : (
              <div className="aspect-square bg-white/5 rounded-xl flex flex-col items-center justify-center gap-4">
                <User className="w-16 h-16 text-white/20" />
                <p className="text-white/40 text-center text-sm px-4">
                  Take a selfie or upload a photo of yourself
                </p>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-3">
              {/* Camera Input */}
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="user"
                className="hidden"
                onChange={(e) => e.target.files[0] && handleSelfieCapture(e.target.files[0])}
                data-testid="camera-input"
              />
              <Button
                variant="outline"
                className="border-white/20 text-white hover:bg-white/10 h-12"
                onClick={() => cameraInputRef.current?.click()}
              >
                <Camera className="w-4 h-4 mr-2" />
                Camera
              </Button>
              
              {/* File Input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => e.target.files[0] && handleSelfieCapture(e.target.files[0])}
                data-testid="file-input"
              />
              <Button
                variant="outline"
                className="border-white/20 text-white hover:bg-white/10 h-12"
                onClick={() => fileInputRef.current?.click()}
              >
                <Image className="w-4 h-4 mr-2" />
                Gallery
              </Button>
            </div>
            
            <Button
              onClick={handleFindMyPhotos}
              className="w-full bg-white text-black hover:bg-white/90 h-12 rounded-full font-semibold"
              disabled={!selfiePreview || searching}
              data-testid="search-with-selfie-btn"
            >
              {searching ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Find My Photos
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Lightbox */}
      <AnimatePresence>
        {selectedPhoto && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/95 z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedPhoto(null)}
            data-testid="lightbox"
          >
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-4 right-4 text-white/60 hover:text-white hover:bg-white/10 z-10"
              onClick={() => setSelectedPhoto(null)}
            >
              <X className="w-6 h-6" />
            </Button>
            
            <Button
              variant="ghost"
              size="icon"
              className="absolute left-4 top-1/2 -translate-y-1/2 text-white/60 hover:text-white hover:bg-white/10"
              onClick={(e) => { e.stopPropagation(); navigatePhoto(-1); }}
            >
              <ChevronLeft className="w-8 h-8" />
            </Button>
            
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-4 top-1/2 -translate-y-1/2 text-white/60 hover:text-white hover:bg-white/10"
              onClick={(e) => { e.stopPropagation(); navigatePhoto(1); }}
            >
              <ChevronRight className="w-8 h-8" />
            </Button>
            
            <motion.img
              key={selectedPhoto.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              src={selectedPhoto.url.startsWith('http') ? selectedPhoto.url : `${BACKEND_URL}${selectedPhoto.url}`}
              alt={selectedPhoto.filename}
              className="max-w-full max-h-[85vh] object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
            
            <a
              href={selectedPhoto.url.startsWith('http') ? selectedPhoto.url : `${BACKEND_URL}${selectedPhoto.url}`}
              download
              target="_blank"
              rel="noopener noreferrer"
              className="absolute bottom-4 left-1/2 -translate-x-1/2 inline-flex items-center gap-2 px-4 py-2 bg-white text-black rounded-full font-medium hover:bg-white/90 transition-colors"
              onClick={(e) => e.stopPropagation()}
              data-testid="download-photo-btn"
            >
              <Download className="w-4 h-4" />
              Download
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
