import React, { useState } from "react";
import Confetti from "react-confetti";
import { motion } from "framer-motion";

function App() {

  const [showPopup, setShowPopup] = useState(false);

  const handleClick = () => {
    setShowPopup(true);
  };

  return (
    <div
      style={{
        backgroundColor: "#FFF7B0",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "Arial"
      }}
    >

      {showPopup && <Confetti numberOfPieces={400} />}

      <h1 style={{marginBottom:"30px"}}>
        Do checkout my first REACT project
      </h1>

      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={handleClick}
        style={{
          backgroundColor: "black",
          color: "white",
          padding: "18px 45px",
          fontSize: "18px",
          border: "none",
          cursor: "pointer",
          textTransform: "uppercase",
          borderRadius: "6px",
          letterSpacing:"2px"
        }}
      >
        CLICK ME
      </motion.button>

      {showPopup && (

        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}

          style={{
            position: "fixed",
            top: "40%",
            background: "white",
            padding: "40px",
            borderRadius: "12px",
            boxShadow: "0px 10px 25px rgba(0,0,0,0.3)",
            textAlign: "center"
          }}
        >

          <h2 style={{fontSize:"40px"}}>👍 😊</h2>

          <p style={{fontSize:"20px"}}>
            I hope you like it !!!!
          </p>

        </motion.div>

      )}

    </div>
  );
}

export default App;