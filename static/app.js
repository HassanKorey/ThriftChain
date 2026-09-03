document.addEventListener("DOMContentLoaded", () => {
    // --- CREATE CIRCLE LOGIC ---
    const form = document.getElementById("create-circle-form");
    if (form) {
        const resultContainer = document.getElementById("result-container");
        const inviteLinkInput = document.getElementById("invite-link");
        const submitBtn = document.getElementById("submit-btn");
        const copyBtn = document.getElementById("copy-btn");

        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            submitBtn.disabled = true;
            submitBtn.textContent = "Creating...";

            const payload = {
                name: document.getElementById("name").value,
                contribution_amount: parseFloat(document.getElementById("amount").value),
                member_count_target: parseInt(document.getElementById("members").value, 10)
            };

            try {
                const response = await fetch("/api/circles", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error("Failed to create circle");
                }

                const circle = await response.json();
                const inviteUrl = `${window.location.origin}/join/${circle.id}`;
                inviteLinkInput.value = inviteUrl;
                
                resultContainer.classList.remove("hidden");
                submitBtn.textContent = "Create Another";
                submitBtn.disabled = false;
                
            } catch (error) {
                console.error(error);
                alert("Error creating circle. Check console.");
                submitBtn.disabled = false;
                submitBtn.textContent = "Create Circle";
            }
        });

        copyBtn.addEventListener("click", () => {
            inviteLinkInput.select();
            document.execCommand("copy");
            copyBtn.textContent = "Copied!";
            setTimeout(() => { copyBtn.textContent = "Copy"; }, 2000);
        });
    }

    // --- JOIN CIRCLE LOGIC ---
    const joinForm = document.getElementById("join-circle-form");
    if (joinForm) {
        const joinSubmitBtn = document.getElementById("join-submit-btn");
        const joinResult = document.getElementById("join-result");

        joinForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            joinSubmitBtn.disabled = true;
            joinSubmitBtn.textContent = "Provisioning Wallet (This takes a moment)...";

            const circleId = joinForm.getAttribute("data-circle-id");
            
            // Randomize suffix for test persona to avoid 409 Conflict in sandbox
            const randSuffix = Math.floor(1000 + Math.random() * 9000);
            let phone = document.getElementById("phone").value;
            let email = document.getElementById("email").value;
            
            if (phone === "+2348000000000") phone = `+23480000${randSuffix}`;
            if (email === "bunch.dillon@example.com") email = `bunch.dillon${randSuffix}@example.com`;

            const payload = {
                name: document.getElementById("name").value,
                email: email,
                phone: phone,
                bvn: document.getElementById("bvn").value,
                dob: document.getElementById("dob").value,
                gender: document.getElementById("gender").value,
                street: document.getElementById("street").value,
                city: document.getElementById("city").value,
                state: document.getElementById("state").value,
                country: document.getElementById("country").value,
            };

            try {
                const response = await fetch(`/api/circles/${circleId}/join`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || "Failed to join circle");
                }

                joinResult.classList.remove("hidden");
                joinSubmitBtn.style.display = "none";
                
            } catch (error) {
                console.error(error);
                alert("Error: " + error.message);
                joinSubmitBtn.disabled = false;
                joinSubmitBtn.textContent = "Join Circle & Create Wallet";
            }
        });
    }
});
