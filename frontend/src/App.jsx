import { useEffect, useState } from "react"
import "./App.css"

function App() {

  // Browser se purani chat directly load
  const [messages, setMessages] = useState(() => {
    const savedMessages = localStorage.getItem("chatHistory")

    if (savedMessages) {
      return JSON.parse(savedMessages)
    }

    return []
  })

  const [message, setMessage] = useState("")


  const sendMessage = async () => {

    if (!message.trim()) return

    // Current message ko alag save kar rahe hain
    const currentMessage = message

    // Sirf previous chats AI ko bhejenge
    // Last 4 exchanges = 8 messages
    const previousHistory = messages.slice(-8)


    // Screen par user message turant dikhao
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        sender: "user",
        text: currentMessage
      }
    ])


    // Input clear
    setMessage("")


    try {

      const response = await fetch(
        "http://127.0.0.1:8000/chat",
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


      const data = await response.json()


      // AI response screen par add
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "ai",
          text: data.answer
        }
      ])

    } catch (error) {

      console.error(error)

      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "ai",
          text: "Sorry, I couldn't connect to the server."
        }
      ])
    }
  }


  // Messages browser mein save
  useEffect(() => {

    localStorage.setItem(
      "chatHistory",
      JSON.stringify(messages)
    )

  }, [messages])


  return (
    <div className="chat-container">

      <div className="chat-header">
        <h2>AJAY AI Assistant</h2>
      </div>


      <div className="chat-messages">

        {messages.map((msg, index) => (

          <div
            key={index}
            className={`message ${msg.sender}`}
          >
            {msg.text}
          </div>

        ))}

      </div>


      <div className="chat-input">

        <input
          type="text"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Type your message..."

          onKeyDown={(event) => {

            if (event.key === "Enter") {
              sendMessage()
            }

          }}
        />


        <button onClick={sendMessage}>
          Send
        </button>

      </div>

    </div>
  )
}

export default App