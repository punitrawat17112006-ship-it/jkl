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

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }
    
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background */}
      <div 
        className="absolute inset-0 bg-cover bg-center opacity-20"
        style={{ backgroundImage: "url('https://images.unsplash.com/photo-1766353846635-00a10ab84157?crop=entropy&cs=srgb&fm=jpg&q=85')" }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/80 to-black" />
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        <Card className="bg-card/80 backdrop-blur-xl border-white/10 shadow-2xl" data-testid="login-card">
          <CardHeader className="text-center space-y-4">
            <motion.div 
              className="mx-auto w-16 h-16 bg-white/10 rounded-2xl flex items-center justify-center"
              whileHover={{ scale: 1.05 }}
            >
              <Camera className="w-8 h-8 text-white" strokeWidth={1.5} />
            </motion.div>
            <div>
              <CardTitle className="text-2xl font-bold tracking-tight text-white">PhotoEvent Pro</CardTitle>
              <CardDescription className="text-muted-foreground mt-2">
                Sign in to manage your photography events
              </CardDescription>
            </div>
          </CardHeader>
          
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-white/80">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="photographer@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-white/5 border-white/10 focus:border-white/30 h-11 text-white placeholder:text-white/40"
                  data-testid="login-email-input"
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
                    data-testid="login-password-input"
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
                data-testid="login-submit-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  "Sign In"
                )}
              </Button>
            </form>
            
            <div className="mt-6 text-center">
              <p className="text-white/50 text-sm">
                Don't have an account?{" "}
                <Link 
                  to="/register" 
                  className="text-white hover:underline font-medium"
                  data-testid="register-link"
                >
                  Create one
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
