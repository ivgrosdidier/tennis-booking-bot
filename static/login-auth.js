import { auth, provider, db } from "./firebase-config.js";

import { createUserWithEmailAndPassword,
         signInWithEmailAndPassword,
         signInWithPopup,
         sendPasswordResetEmail,
         onAuthStateChanged} from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";

import {
    setDoc, 
    getDoc, 
    doc 
} from "https://www.gstatic.com/firebasejs/10.9.0/firebase-firestore.js";

/* == UI - Elements == */
const signInWithGoogleButtonEl = document.getElementById("sign-in-with-google-btn")
const signUpWithGoogleButtonEl = document.getElementById("sign-up-with-google-btn")
const emailInputEl = document.getElementById("email-input")
const passwordInputEl = document.getElementById("password-input")
const signInButtonEl = document.getElementById("sign-in-btn")
const createAccountButtonEl = document.getElementById("create-account-btn")
const emailForgotPasswordEl = document.getElementById("email-forgot-password")
const forgotPasswordButtonEl = document.getElementById("forgot-password-btn")

const errorMsgEmail = document.getElementById("email-error-message")
const errorMsgPassword = document.getElementById("password-error-message")
const errorMsgGoogleSignIn = document.getElementById("google-signin-error-message")



/* == UI - Event Listeners == */
if (signInWithGoogleButtonEl && signInButtonEl) {
    signInWithGoogleButtonEl.addEventListener("click", authSignInWithGoogle)
    signInButtonEl.addEventListener("click", authSignInWithEmail)
}

if (createAccountButtonEl) {
    createAccountButtonEl.addEventListener("click", authCreateAccountWithEmail)
}

if (signUpWithGoogleButtonEl) {
    signUpWithGoogleButtonEl.addEventListener("click", authSignUpWithGoogle)
}

if (forgotPasswordButtonEl) {
    forgotPasswordButtonEl.addEventListener("click", resetPassword)
}

/* == Auth State Observer ==
   This is the safety net. Fires on every sign in no matter what.
   Ensures Firestore doc always exists with correct fields. */
onAuthStateChanged(auth, async (user) => {
    if (user) {
        await ensureUserDocument(user)
    }
})


/* == Firestore User Document ==
   Safe to call on every sign in.
   Only writes if document doesn't exist yet — never overwrites. */
async function ensureUserDocument(user) {
    try {
        const userRef = doc(db, "users", user.uid)
        const userSnap = await getDoc(userRef)

        if (!userSnap.exists()) {
            await setDoc(userRef, {
                created_at: new Date().toISOString().split('T')[0],
                email: user.email,
                autobook_enabled: false,
                google_calendar_connected: false,
                club_profile_connected: false,
                user_id: user.uid
            })
            console.log("[Firestore] New user document created for:", user.email)
        } else {
            console.log("[Firestore] Existing user document found for:", user.email)
        }
    } catch (error) {
        console.error("[Firestore] Failed to ensure user document:", error.code, error.message)
    }
}

/* === Main Code === */

/* = Functions - Firebase - Authentication = */

async function authSignInWithGoogle() {
    provider.setCustomParameters({ 'prompt': 'select_account' })
    try {
        const result = await signInWithPopup(auth, provider)
        const user = result.user
        const idToken = await user.getIdToken()  // ✅ defined before use
        loginUser(user, idToken, '/dashboard')
    } catch (error) {
        console.error("Google sign in error:", error.message)
    }
}

async function authSignUpWithGoogle() {
    provider.setCustomParameters({ 'prompt': 'select_account' })
    try {
        const result = await signInWithPopup(auth, provider)
        const user = result.user
        const idToken = await user.getIdToken()  // ✅ defined before use

        // Check if new or returning user to decide where to redirect
        const userSnap = await getDoc(doc(db, "users", user.uid))
        const isNewUser = !userSnap.exists()

        // ensureUserDocument will run via onAuthStateChanged automatically
        // but we can also call it directly here to guarantee timing
        await ensureUserDocument(user)

        // Redirect new users to onboarding, returning users to dashboard
        loginUser(user, idToken, isNewUser ? '/instructions' : '/dashboard')

    } catch (error) {
        console.error("Google sign up error:", error.message)
    }
}

function authSignInWithEmail() {
    const email = emailInputEl.value
    const password = passwordInputEl.value

    signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            const user = userCredential.user
            user.getIdToken().then(idToken => loginUser(user, idToken, '/dashboard'))
        })
        .catch((error) => {
            if (error.code === "auth/invalid-email") {
                errorMsgEmail.textContent = "Invalid email"
            } else if (error.code === "auth/invalid-credential") {
                errorMsgPassword.textContent = "Login failed - invalid email or password"
            }
        })
}

async function authCreateAccountWithEmail() {
    const email = emailInputEl.value
    const password = passwordInputEl.value

    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password)
        const user = userCredential.user
        console.log("[Auth] Account created for:", user.email)

        // Explicitly create the Firestore doc here too
        // onAuthStateChanged will also fire but this guarantees it before redirect
        await ensureUserDocument(user)

        const idToken = await user.getIdToken()
        loginUser(user, idToken, '/instructions')

    } catch (error) {
        console.error("[Auth] Signup error:", error.code, error.message)
        if (error.code === "auth/invalid-email") {
            errorMsgEmail.textContent = "Invalid email"
        } else if (error.code === "auth/weak-password") {
            errorMsgPassword.textContent = "Must be at least 6 characters"
        } else if (error.code === "auth/email-already-in-use") {
            errorMsgEmail.textContent = "An account already exists for this email"
        }
    }
}

function resetPassword() {
    const emailToReset = emailForgotPasswordEl.value
    clearInputField(emailForgotPasswordEl)

    sendPasswordResetEmail(auth, emailToReset)
        .then(() => {
            document.getElementById("reset-password-view").style.display = "none"
            document.getElementById("reset-password-confirmation-page").style.display = "block"
        })
        .catch((error) => {
            console.error("Password reset error:", error.code)
        })
}

function loginUser(user, idToken, redirectPath = '/dashboard') {
    fetch('/auth', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${idToken}`
        },
        credentials: 'same-origin'
    }).then(response => {
        if (response.ok) {
            window.location.href = redirectPath
        } else {
            console.error('Flask auth failed')
        }
    }).catch(error => {
        console.error('Fetch error:', error)
    })
}



// /* = Functions - UI = */
function clearInputField(field) {
	field.value = ""
}

function clearAuthFields() {
	clearInputField(emailInputEl)
	clearInputField(passwordInputEl)
}


