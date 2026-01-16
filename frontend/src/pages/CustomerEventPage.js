import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Camera, Image, Loader2, Download, ChevronLeft, ChevronRight, X } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { toast } from "sonner";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function CustomerEventPage() {
  const { eventId } = useParams();
  const [event, setEvent] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);

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

  const navigatePhoto = (direction) => {
    const currentIndex = photos.findIndex(p => p.id === selectedPhoto.id);
    let newIndex = currentIndex + direction;
    if (newIndex < 0) newIndex = photos.length - 1;
    if (newIndex >= photos.length) newIndex = 0;
    setSelectedPhoto(photos[newIndex]);
  };

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
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Event Info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <p className="text-white/60 max-w-lg mx-auto">
            {event?.description || "Browse through the photos from this event"}
          </p>
          <div className="flex items-center justify-center gap-2 mt-4 text-white/50">
            <Image className="w-4 h-4" />
            <span>{photos.length} photos available</span>
          </div>
        </motion.div>

        {/* Photo Grid */}
        {photos.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Image className="w-10 h-10 text-white/20" />
            </div>
            <h2 className="text-xl font-semibold text-white/60 mb-2" style={{ fontFamily: 'Manrope' }}>
              No photos yet
            </h2>
            <p className="text-white/40">Photos will appear here once uploaded</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-4">
            <AnimatePresence>
              {photos.map((photo, index) => (
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
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="text-white text-sm font-medium">View</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </main>

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
              data-testid="close-lightbox-btn"
            >
              <X className="w-6 h-6" />
            </Button>
            
            <Button
              variant="ghost"
              size="icon"
              className="absolute left-4 top-1/2 -translate-y-1/2 text-white/60 hover:text-white hover:bg-white/10"
              onClick={(e) => { e.stopPropagation(); navigatePhoto(-1); }}
              data-testid="prev-photo-btn"
            >
              <ChevronLeft className="w-8 h-8" />
            </Button>
            
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-4 top-1/2 -translate-y-1/2 text-white/60 hover:text-white hover:bg-white/10"
              onClick={(e) => { e.stopPropagation(); navigatePhoto(1); }}
              data-testid="next-photo-btn"
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
