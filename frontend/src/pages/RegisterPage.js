import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Camera, Eye, EyeOff, Loader2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password) {
      toast.error("Please fill in all fields");
      return;
    }
    if (password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    
    setLoading(true);
    try {
      await register(email, password, name);
      toast.success("Account created successfully!");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background */}
      <div 
        className="absolute inset-0 bg-cover bg-center opacity-20"
        style={{ backgroundImage: "url('https://images.unsplash.com/photo-1763256377588-f29bdc912698?crop=entropy&cs=srgb&fm=jpg&q=85')" }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/80 to-black" />
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <Card className="bg-card/80 backdrop-blur-xl border-white/10 shadow-2xl" data-testid="register-card">
          <CardHeader className="text-center space-y-4">
            <motion.div 
              className="mx-auto w-16 h-16 bg-white/10 rounded-2xl flex items-center justify-center"
              whileHover={{ scale: 1.05 }}
            >
              <Camera className="w-8 h-8 text-white" strokeWidth={1.5} />
            </motion.div>
            <div>
              <CardTitle className="text-2xl font-bold tracking-tight text-white">Create Account</CardTitle>
              <CardDescription className="text-muted-foreground mt-2">
                Start managing your event photography
              </CardDescription>
            </div>
          </CardHeader>
          
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-white/80">Full Name</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="bg-white/5 border-white/10 focus:border-white/30 h-11 text-white placeholder:text-white/40"
                  data-testid="register-name-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="email" className="text-white/80">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="photographer@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-white/5 border-white/10 focus:border-white/30 h-11 text-white placeholder:text-white/40"
                  data-testid="register-email-input"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="password" className="text-white/80">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="bg-white/5 border-white/10 focus:border-white/30 h-11 text-white placeholder:text-white/40 pr-10"
                    data-testid="register-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              
              <Button 
                type="submit" 
                className="w-full h-11 bg-white text-black hover:bg-white/90 font-semibold rounded-full transition-all duration-300"
                disabled={loading}
                data-testid="register-submit-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  "Create Account"
                )}
              </Button>
            </form>
            
            <div className="mt-6 text-center">
              <p className="text-white/50 text-sm">
                Already have an account?{" "}
                <Link 
                  to="/login" 
                  className="text-white hover:underline font-medium"
                  data-testid="login-link"
                >
                  Sign in
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
