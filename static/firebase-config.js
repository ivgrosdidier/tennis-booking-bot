import { initializeApp } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import { getAuth, 
         GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.9.0/firebase-firestore.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDaty9NLJFbFjb0QpLxHeGnx2JllctPBAE",
  authDomain: "tennis-booking-caadb.firebaseapp.com",
  projectId: "tennis-booking-caadb",
  storageBucket: "tennis-booking-caadb.firebasestorage.app",
  messagingSenderId: "6814010094",
  appId: "1:6814010094:web:4ab67c40adc60d9cc241ff"
};

  // Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

const db = getFirestore(app);

export { auth, provider, db };