import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Camera, Calendar, Image, LogOut, Loader2, Trash2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DashboardPage() {
  const { user, logout, getAuthHeaders } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newEvent, setNewEvent] = useState({ name: "", description: "", date: "" });

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${API}/events`, { headers: getAuthHeaders() });
      setEvents(response.data);
    } catch (error) {
      toast.error("Failed to load events");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEvent = async (e) => {
    e.preventDefault();
    if (!newEvent.name) {
      toast.error("Please enter an event name");
      return;
    }
    
    setCreating(true);
    try {
      const response = await axios.post(`${API}/events`, newEvent, { headers: getAuthHeaders() });
      setEvents([response.data, ...events]);
      setNewEvent({ name: "", description: "", date: "" });
      setDialogOpen(false);
      toast.success("Event created successfully!");
    } catch (error) {
      toast.error("Failed to create event");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteEvent = async (eventId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this event?")) return;
    
    try {
      await axios.delete(`${API}/events/${eventId}`, { headers: getAuthHeaders() });
      setEvents(events.filter(ev => ev.id !== eventId));
      toast.success("Event deleted");
    } catch (error) {
      toast.error("Failed to delete event");
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-white/5 bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center">
              <Camera className="w-5 h-5 text-white" strokeWidth={1.5} />
            </div>
            <span className="text-xl font-bold tracking-tight text-white" style={{ fontFamily: 'Manrope' }}>
              PhotoEvent Pro
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            <span className="text-white/60 text-sm hidden sm:block">{user?.name}</span>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={handleLogout}
              className="text-white/60 hover:text-white hover:bg-white/10"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats & Create */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white" style={{ fontFamily: 'Manrope' }}>
              Your Events
            </h1>
            <p className="text-muted-foreground mt-1">
              {events.length} {events.length === 1 ? "event" : "events"} total
            </p>
          </div>
          
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                className="bg-white text-black hover:bg-white/90 rounded-full px-6 font-semibold shadow-[0_0_20px_rgba(255,255,255,0.1)]"
                data-testid="create-event-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Event
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-card border-white/10 text-white" data-testid="create-event-dialog">
              <DialogHeader>
                <DialogTitle className="text-xl font-bold" style={{ fontFamily: 'Manrope' }}>Create New Event</DialogTitle>
                <DialogDescription className="text-muted-foreground">
                  Add a new photography event to get started
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateEvent} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="event-name" className="text-white/80">Event Name</Label>
                  <Input
                    id="event-name"
                    placeholder="Wedding - John & Jane"
                    value={newEvent.name}
                    onChange={(e) => setNewEvent({ ...newEvent, name: e.target.value })}
                    className="bg-white/5 border-white/10 focus:border-white/30 h-11 text-white"
                    data-testid="event-name-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="event-desc" className="text-white/80">Description (Optional)</Label>
                  <Input
                    id="event-desc"
                    placeholder="Beach wedding ceremony"
                    value={newEvent.description}
                    onChange={(e) => setNewEvent({ ...newEvent, description: e.target.value })}
                    className="bg-white/5 border-white/10 focus:border-white/30 h-11 text-white"
                    data-testid="event-description-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="event-date" className="text-white/80">Event Date</Label>
                  <Input
                    id="event-date"
                    type="date"
                    value={newEvent.date}
                    onChange={(e) => setNewEvent({ ...newEvent, date: e.target.value })}
                    className="bg-white/5 border-white/10 focus:border-white/30 h-11 text-white"
                    data-testid="event-date-input"
                  />
                </div>
                <Button 
                  type="submit" 
                  className="w-full bg-white text-black hover:bg-white/90 h-11 rounded-full font-semibold"
                  disabled={creating}
                  data-testid="submit-create-event-btn"
                >
                  {creating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    "Create Event"
                  )}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Events Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-white/40" />
          </div>
        ) : events.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-20"
          >
            <div className="w-20 h-20 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Calendar className="w-10 h-10 text-white/30" />
            </div>
            <h3 className="text-xl font-semibold text-white/60 mb-2" style={{ fontFamily: 'Manrope' }}>
              No events yet
            </h3>
            <p className="text-white/40 mb-6">Create your first event to start uploading photos</p>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AnimatePresence>
              {events.map((event, index) => (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card 
                    className="bg-card border-white/5 hover:border-white/10 hover:bg-white/[0.02] transition-all duration-300 cursor-pointer group"
                    onClick={() => navigate(`/events/${event.id}`)}
                    data-testid={`event-card-${event.id}`}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <CardTitle className="text-lg font-semibold text-white truncate" style={{ fontFamily: 'Manrope' }}>
                            {event.name}
                          </CardTitle>
                          {event.description && (
                            <CardDescription className="text-white/50 mt-1 line-clamp-1">
                              {event.description}
                            </CardDescription>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-white/40 hover:text-red-400 hover:bg-red-400/10"
                          onClick={(e) => handleDeleteEvent(event.id, e)}
                          data-testid={`delete-event-${event.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-4 text-sm text-white/50">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-4 h-4" />
                          <span>{event.date}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Image className="w-4 h-4" />
                          <span>{event.photo_count} photos</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </main>
    </div>
  );
}
