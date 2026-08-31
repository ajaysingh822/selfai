import { useEffect, useState } from "react"
import "./App.css"

function App() {
  // Browser se purani chat load
  const [messages, setMessages] = useState(() => {
    const savedMessages = localStorage.getItem("chatHistory")

    if (savedMessages) {
      return JSON.parse(savedMessages)
    }

    return []
  })

  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)


  // Chat ko browser mein save karna
  useEffect(() => {
    localStorage.setItem(
      "chatHistory",
      JSON.stringify(messages)
    )
  }, [messages])


  // Message send
  const sendMessage = async () => {
    if (!message.trim() || loading) return

    const currentMessage = message.trim()

    // Last 4 exchanges = 8 messages
    const previousHistory = messages.slice(-8)

    // User message screen par show
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        sender: "user",
        text: currentMessage
      }
    ])

    // Input clear
    setMessage("")

    // Loading start
    setLoading(true)

    try {
      const response = await fetch(
        "https://selfai-0tph.onrender.com/chat",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json"
          },

          body: JSON.stringify({
            message: currentMessage,
            history: previousHistory
          })
        }
      )

      if (!response.ok) {
        throw new Error("Server error")
      }

      const data = await response.json()

      // AI response show
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "ai",
          text: data.answer
        }
      ])
    }

    catch (error) {
      console.error(error)

      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "ai",
          text: "Sorry, something went wrong."
        }
      ])
    }

    finally {
      setLoading(false)
    }
  }


  return (
    <div className="chat-container">

      {/* Header */}
      <div className="chat-header">
        <h2>AJAY AI Assistant</h2>
      </div>


      {/* Messages */}
      <div className="chat-messages">

        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.sender}`}
          >
            {msg.text}
          </div>
        ))}


        {/* AI loading */}
        {loading && (
          <div className="message ai">
            Thinking...
          </div>
        )}

      </div>


      {/* Input */}
      <div className="chat-input">

        <input
          type="text"
          value={message}
          onChange={(event) =>
            setMessage(event.target.value)
          }
          placeholder="Type your message..."

          onKeyDown={(event) => {
            if (event.key === "Enter") {
              sendMessage()
            }
          }}
        />

        <button
          onClick={sendMessage}
          disabled={loading}
        >
          {loading ? "..." : "Send"}
        </button>

      </div>

    </div>
  )
}

export default App