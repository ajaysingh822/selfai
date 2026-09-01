import { useEffect, useState } from "react";
import { supabase } from "./lib/supabase";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [user, setUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);

  // =========================================================
  // GET CURRENT SESSION + LISTEN FOR LOGIN / LOGOUT
  // =========================================================

  useEffect(() => {
    let mounted = true;

    const getSession = async () => {
      const {
        data: { session },
        error,
      } = await supabase.auth.getSession();

      if (error) {
        console.error("Session error:", error);
      }

      if (mounted) {
        setUser(session?.user ?? null);
        setAuthLoading(false);
      }
    };

    getSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setAuthLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  // =========================================================
  // SAVE / UPDATE USER PROFILE
  // =========================================================

  useEffect(() => {
    if (!user) return;

    const saveProfile = async () => {
      const metadata = user.user_metadata || {};

      const profile = {
        id: user.id,
        email: user.email || null,
        name:
          metadata.full_name ||
          metadata.name ||
          user.email?.split("@")[0] ||
          "User",
        avatar_url:
          metadata.avatar_url ||
          metadata.picture ||
          null,
      };

      const { error } = await supabase
        .from("profiles")
        .upsert(profile, {
          onConflict: "id",
        });

      if (error) {
        console.error("Profile save error:", error);
      }
    };

    saveProfile();
  }, [user]);

  // =========================================================
  // LOAD USER'S CHAT FROM SUPABASE
  // =========================================================

  useEffect(() => {
    if (!user) {
      setMessages([]);
      return;
    }

    const loadMessages = async () => {
      setChatLoading(true);

      const { data, error } = await supabase
        .from("messages")
        .select("id, role, message, created_at")
        .eq("user_id", user.id)
        .order("created_at", {
          ascending: true,
        });

      if (error) {
        console.error("Chat loading error:", error);
        setChatLoading(false);
        return;
      }

      const formattedMessages = (data || []).map((item) => ({
        id: item.id,
        sender: item.role === "assistant" ? "ai" : "user",
        text: item.message,
        created_at: item.created_at,
      }));

      setMessages(formattedMessages);
      setChatLoading(false);
    };

    loadMessages();
  }, [user]);

  // =========================================================
  // GOOGLE LOGIN
  // =========================================================

  const signInWithGoogle = async () => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: window.location.origin,
        },
      });

      if (error) {
        console.error("Google login error:", error);
        alert("Unable to continue with Google.");
      }
    } catch (error) {
      console.error("Google login exception:", error);
      alert("Something went wrong.");
    }
  };

  // =========================================================
  // LOGOUT
  // =========================================================

  const logout = async () => {
    const { error } = await supabase.auth.signOut();

    if (error) {
      console.error("Logout error:", error);
      return;
    }

    setUser(null);
    setMessages([]);
    setMessage("");
  };

  // =========================================================
  // SAVE MESSAGE TO SUPABASE
  // =========================================================

  const saveMessage = async (role, text) => {
    if (!user || !text?.trim()) {
      return null;
    }

    const { data, error } = await supabase
      .from("messages")
      .insert({
        user_id: user.id,
        role,
        message: text.trim(),
      })
      .select("id, role, message, created_at")
      .single();

    if (error) {
      console.error(`${role} message save error:`, error);
      throw error;
    }

    return data;
  };

  // =========================================================
  // SEND CHAT MESSAGE
  // =========================================================

  const sendMessage = async () => {
    if (!message.trim() || loading || !user) {
      return;
    }

    if (!API_URL) {
      console.error("VITE_API_URL is missing.");
      return;
    }

    const currentMessage = message.trim();

    // Previous conversation for AI context
    const previousHistory = messages.slice(-10).map((item) => ({
      role: item.sender === "ai" ? "assistant" : "user",
      message: item.text,
    }));

    // Clear input immediately
    setMessage("");

    // Start loading
    setLoading(true);

    // Temporary message for instant UI
    const temporaryUserMessage = {
      id: `temp-user-${Date.now()}`,
      sender: "user",
      text: currentMessage,
    };

    setMessages((prev) => [
      ...prev,
      temporaryUserMessage,
    ]);

    try {
      // -------------------------------------------------------
      // 1. SAVE USER MESSAGE
      // -------------------------------------------------------

      const savedUserMessage = await saveMessage(
        "user",
        currentMessage
      );

      if (savedUserMessage) {
        setMessages((prev) =>
          prev.map((item) =>
            item.id === temporaryUserMessage.id
              ? {
                  ...item,
                  id: savedUserMessage.id,
                  created_at:
                    savedUserMessage.created_at,
                }
              : item
          )
        );
      }

      // -------------------------------------------------------
      // 2. CALL BACKEND
      // -------------------------------------------------------

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          message: currentMessage,
          history: previousHistory,
        }),
      });

      if (!response.ok) {
        throw new Error(
          `Server error: ${response.status}`
        );
      }

      const data = await response.json();

      const answer =
        typeof data?.answer === "string"
          ? data.answer.trim()
          : "";

      if (!answer) {
        throw new Error("Empty AI response");
      }

      // -------------------------------------------------------
      // 3. SHOW AI RESPONSE
      // -------------------------------------------------------

      const temporaryAIMessage = {
        id: `temp-ai-${Date.now()}`,
        sender: "ai",
        text: answer,
      };

      setMessages((prev) => [
        ...prev,
        temporaryAIMessage,
      ]);

      // -------------------------------------------------------
      // 4. SAVE AI RESPONSE
      // -------------------------------------------------------

      try {
        const savedAssistantMessage = await saveMessage(
          "assistant",
          answer
        );

        if (savedAssistantMessage) {
          setMessages((prev) =>
            prev.map((item) =>
              item.id === temporaryAIMessage.id
                ? {
                    ...item,
                    id: savedAssistantMessage.id,
                    created_at:
                      savedAssistantMessage.created_at,
                  }
                : item
            )
          );
        }
      } catch (saveError) {
        // AI response already works on screen.
        // Only Supabase save failed.
        console.error(
          "AI response save failed:",
          saveError
        );
      }
    } catch (error) {
      console.error("Chat error:", error);

      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          sender: "ai",
          text:
            "Sorry, I couldn't respond right now. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // ENTER KEY
  // =========================================================

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  // =========================================================
  // AUTH LOADING
  // =========================================================

  if (authLoading) {
    return (
      <div className="auth-loading">
        <div className="auth-loading-content">
          <h2>AJAY AI</h2>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  // =========================================================
  // LOGIN PAGE
  // =========================================================

  if (!user) {
    return (
      <div className="login-container">
        <div className="login-card">

          <div className="login-logo">
            AJAY AI
          </div>

          <h1>
            Meet Ajay's
            <br />
            Personal AI
          </h1>

          <p className="login-description">
            Chat naturally with Ajay's AI assistant.
            Ask about Ajay, his work, projects,
            education, skills and more.
          </p>

          <button
            className="google-login-button"
            onClick={signInWithGoogle}
          >
            <span className="google-icon">
              G
            </span>

            Continue with Google
          </button>

          <p className="login-note">
            Sign in to start chatting
          </p>

        </div>
      </div>
    );
  }

  // =========================================================
  // USER INFORMATION
  // =========================================================

  const userMetadata = user.user_metadata || {};

  const userName =
    userMetadata.full_name ||
    userMetadata.name ||
    user.email?.split("@")[0] ||
    "User";

  const userAvatar =
    userMetadata.avatar_url ||
    userMetadata.picture ||
    null;

  // =========================================================
  // CHAT PAGE
  // =========================================================

  return (
    <div className="chat-container">

      {/* HEADER */}

      <div className="chat-header">

        <div className="chat-header-left">

          <div className="ai-avatar">
            A
          </div>

          <div>
            <h2>AJAY AI</h2>

            <span>
              Personal AI Assistant
            </span>
          </div>

        </div>

        <div className="chat-user">

          {userAvatar ? (
            <img
              src={userAvatar}
              alt="User avatar"
              className="user-avatar"
            />
          ) : (
            <div className="user-avatar fallback">
              {userName
                .charAt(0)
                .toUpperCase()}
            </div>
          )}

          <button
            className="logout-button"
            onClick={logout}
          >
            Logout
          </button>

        </div>

      </div>

      {/* MESSAGES */}

      <div className="chat-messages">

        {chatLoading ? (
          <div className="chat-status">
            Loading your conversation...
          </div>
        ) : messages.length === 0 ? (
          <div className="welcome-message">

            <div className="welcome-avatar">
              A
            </div>

            <h3>
              Hey {userName.split(" ")[0]} 👋
            </h3>

            <p>
              I'm Ajay's personal AI assistant.
              Ask me anything about Ajay,
              his work, projects or just
              have a conversation.
            </p>

          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`message ${msg.sender}`}
            >
              {msg.text}
            </div>
          ))
        )}

        {/* THINKING */}

        {loading && (
          <div className="message ai thinking-message">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}

      </div>

      {/* INPUT */}

      <div className="chat-input">

        <input
          type="text"
          value={message}
          onChange={(event) =>
            setMessage(event.target.value)
          }
          onKeyDown={handleKeyDown}
          placeholder="Message AJAY AI..."
          disabled={loading}
        />

        <button
          onClick={sendMessage}
          disabled={
            loading ||
            !message.trim()
          }
        >
          {loading ? "..." : "Send"}
        </button>

      </div>

    </div>
  );
}

export default App;