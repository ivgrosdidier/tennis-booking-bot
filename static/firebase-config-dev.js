import { initializeApp } from "https://www.gstatic.com/firebasejs/12.11.0/firebase-app.js";
import { getAuth, 
         GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/12.11.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/12.11.0/firebase-firestore.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCor_mQHUgfjjNxXjOvTx2vfeSo9PlEklY",
  authDomain: "tennis-booking-dev-29d17.firebaseapp.com",
  projectId: "tennis-booking-dev-29d17",
  storageBucket: "tennis-booking-dev-29d17.firebasestorage.app",
  messagingSenderId: "254873357384",
  appId: "1:254873357384:web:04fe26b00ce0e28971dc7d",
  measurementId: "G-HBBLCF156V"
};

  // Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

const db = getFirestore(app);

export { auth, provider, db };