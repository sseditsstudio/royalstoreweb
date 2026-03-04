// State Management
let cart = [];
let userToken = localStorage.getItem('userToken');
let userRole = localStorage.getItem('userRole');
let captchaAnswer = 0;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateAuthUI();
    fetchProducts();
    generateCaptcha();

    // As per requirement: "each time a person opens the website it must ask for sign up or sign in"
    if (!userToken) {
        showAuth();
    }
});

// Auth Flow
function updateAuthUI() {
    if (userToken) {
        document.getElementById('authLink').style.display = 'none';
        document.getElementById('logoutLink').style.display = 'inline';
        if (userRole === 'admin') {
            document.getElementById('adminLink').style.display = 'inline';
        }
    } else {
        document.getElementById('authLink').style.display = 'inline';
        document.getElementById('logoutLink').style.display = 'none';
        document.getElementById('adminLink').style.display = 'none';
    }
}

function logout() {
    localStorage.removeItem('userToken');
    localStorage.removeItem('userRole');
    userToken = null;
    userRole = null;
    updateAuthUI();
    alert('Logged out successfully.');
    fetchProducts(); // refresh products w/o user history
}

function showAuth() {
    document.getElementById('authModal').style.display = 'flex';
    document.getElementById('authStep1').style.display = 'block';
    document.getElementById('authStep2').style.display = 'none';
    document.getElementById('authMessage').innerText = '';
    generateCaptcha();
}

function generateCaptcha() {
    const num1 = Math.floor(Math.random() * 10);
    const num2 = Math.floor(Math.random() * 10);
    captchaAnswer = num1 + num2;
    document.getElementById('captchaMath').innerText = `${num1} + ${num2} = `;
    document.getElementById('captchaInput').value = '';
}

async function requestOTP() {
    const contact = document.getElementById('contactInput').value;
    const captcha = parseInt(document.getElementById('captchaInput').value);

    if (captcha !== captchaAnswer) {
        document.getElementById('authMessage').innerText = 'Incorrect CAPTCHA.';
        generateCaptcha();
        return;
    }
    if (!contact) {
        document.getElementById('authMessage').innerText = 'Please enter email/phone.';
        return;
    }

    try {
        const res = await fetch('/api/request-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contact, captcha: 'verified' }) // backend trusts verified string in this demo
        });
        const data = await res.json();

        if (res.ok) {
            document.getElementById('authStep1').style.display = 'none';
            document.getElementById('authStep2').style.display = 'block';
            document.getElementById('authMessage').innerText = 'OTP Sent! (Check email/terminal)';
        } else {
            document.getElementById('authMessage').innerText = data.detail || 'Error sending OTP';
            generateCaptcha();
        }
    } catch (e) {
        document.getElementById('authMessage').innerText = 'Server error.';
    }
}

async function verifyOTP() {
    const contact = document.getElementById('contactInput').value;
    const otp = document.getElementById('otpInput').value;

    try {
        const res = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contact, otp })
        });
        const data = await res.json();

        if (res.ok) {
            localStorage.setItem('userToken', data.access_token);
            localStorage.setItem('userRole', data.role);
            userToken = data.access_token;
            userRole = data.role;

            closeModals();
            updateAuthUI();
            fetchProducts();
            alert('Successfully logged in.');
        } else {
            document.getElementById('authMessage').innerText = data.detail || 'Invalid OTP';
        }
    } catch (e) {
        document.getElementById('authMessage').innerText = 'Server error.';
    }
}

// Products
async function fetchProducts(query = '') {
    const headers = {};
    if (userToken) headers['Authorization'] = `Bearer ${userToken}`;

    const url = query ? `/api/products?query=${encodeURIComponent(query)}` : '/api/products';

    try {
        const res = await fetch(url, { headers });
        const data = await res.json();

        const grid = document.getElementById('productsSection');
        grid.innerHTML = '';

        if (data.message && data.items.length === 0) {
            grid.innerHTML = `<h3 style="grid-column: 1/-1; text-align: center;">${data.message}</h3>`;
            return;
        }

        data.items.forEach(p => {
            const el = document.createElement('div');
            el.className = 'product-card';
            // Use loremflickr with specific width/height and id as cache buster to load unique images
            const imgUrl = p.image_url || `https://loremflickr.com/400/300/${encodeURIComponent(p.name)}?lock=${p.id}`;
            el.innerHTML = `
                <img src="${imgUrl}" alt="${p.name}">
                <h3>${p.name}</h3>
                <p>₹${p.price.toFixed(2)}</p>
                <button class="action-btn" onclick="addToCart(${p.id}, '${p.name}', ${p.price})">Add to Cart</button>
            `;
            grid.appendChild(el);
        });
    } catch (e) {
        console.error("Failed to load products", e);
    }
}

function searchProducts() {
    const query = document.getElementById('searchInput').value;
    fetchProducts(query);
}

// Cart
function addToCart(id, name, price) {
    const existing = cart.find(i => i.id === id);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ id, name, price, quantity: 1 });
    }
    updateCartIcon();
    alert(`${name} added to cart.`);
}

function updateCartIcon() {
    const count = cart.reduce((acc, i) => acc + i.quantity, 0);
    document.getElementById('cartCount').innerText = count;
}

function showCart() {
    document.getElementById('cartModal').style.display = 'flex';
    renderCart();
}

function renderCart() {
    const itemsContainer = document.getElementById('cartItems');
    itemsContainer.innerHTML = '';
    let subtotal = 0;

    cart.forEach((item, index) => {
        subtotal += item.price * item.quantity;
        const el = document.createElement('div');
        el.className = 'cart-item';
        el.innerHTML = `
            <span>${item.name} (${item.quantity})</span>
            <span>₹${(item.price * item.quantity).toFixed(2)}</span>
            <button onclick="removeFromCart(${index})" style="background:transparent;border:none;color:white;cursor:pointer;">&times;</button>
        `;
        itemsContainer.appendChild(el);
    });

    document.getElementById('cartSubtotal').innerText = subtotal.toFixed(2);
}

function removeFromCart(index) {
    cart.splice(index, 1);
    updateCartIcon();
    renderCart();
}

function toggleDeliveryFields() {
    const isHome = document.querySelector('input[name="deliveryType"]:checked').value === 'home';
    document.getElementById('homeDeliveryFields').style.display = isHome ? 'block' : 'none';
}

async function checkout() {
    if (!userToken) {
        alert("Please sign in to place an order.");
        showAuth();
        return;
    }

    if (cart.length === 0) {
        alert("Cart is empty.");
        return;
    }

    const deliveryType = document.querySelector('input[name="deliveryType"]:checked').value;
    const address = document.getElementById('addressInput').value;
    const distance = parseFloat(document.getElementById('distanceInput').value || 0);

    if (deliveryType === 'home' && (!address || isNaN(distance))) {
        alert("Please provide valid address and distance for home delivery.");
        return;
    }

    const payload = {
        items: cart,
        delivery_type: deliveryType,
        address: address,
        distance_km: distance
    };

    try {
        const res = await fetch('/api/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok) {
            let msg = `Order placed successfully! Total: ₹${data.total.toFixed(2)}. Code: ${data.unique_code}.`;
            if (deliveryType === 'home') {
                if (distance <= 15) {
                    msg += " Enjoy your free delivery!";
                } else {
                    msg += ` Included delivery charge: ₹${data.delivery_charge.toFixed(2)}.`;
                }
            } else {
                msg += " Data has been sent to the administrator.";
            }

            alert(msg);
            cart = [];
            updateCartIcon();
            closeModals();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        alert("Server error.");
    }
}

// AI Assistant
function toggleAI() {
    const body = document.getElementById('aiBody');
    const icon = document.getElementById('aiToggleIcon');
    if (body.style.display === 'none') {
        body.style.display = 'flex';
        icon.innerText = 'v';
    } else {
        body.style.display = 'none';
        icon.innerText = '^';
    }
}

async function sendAIMessage() {
    const input = document.getElementById('aiInput');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    const container = document.getElementById('aiMessages');

    container.innerHTML += `<div class="msg user-msg">${msg}</div>`;
    container.scrollTop = container.scrollHeight;

    try {
        const res = await fetch('/api/ai-assistant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();

        container.innerHTML += `<div class="msg ai-msg">${data.reply}</div>`;
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        container.innerHTML += `<div class="msg ai-msg">Offline...</div>`;
    }
}

// Admin
async function showAdmin() {
    document.getElementById('adminModal').style.display = 'flex';

    try {
        const res = await fetch('/api/admin/setup', {
            headers: { 'Authorization': `Bearer ${userToken}` }
        });
        const data = await res.json();

        if (res.ok) {
            const container = document.getElementById('adminProducts');
            container.innerHTML = '<h3>Manage Products</h3>';

            const list = document.createElement('div');
            data.products.forEach(p => {
                list.innerHTML += `
                    <div style="display:flex; justify-content:space-between; margin-bottom:10px; padding:10px; border:1px solid #3a8ded; border-radius:10px;">
                        <span>ID: ${p.id} | ${p.name} </span>
                        <div>
                            <input type="number" id="price-${p.id}" value="${p.price}" style="width:80px; padding:5px; margin:0;" />
                            <select id="avail-${p.id}" style="padding:5px;">
                                <option value="1" ${p.available ? 'selected' : ''}>Available</option>
                                <option value="0" ${!p.available ? 'selected' : ''}>Hidden</option>
                            </select>
                            <button class="action-btn" style="width:auto; padding:5px 10px;" onclick="updateProduct(${p.id})">Save</button>
                        </div>
                    </div>
                `;
            });
            container.appendChild(list);
        }
    } catch (e) {
        alert("Admin load error");
    }
}

async function updateProduct(id) {
    const price = parseFloat(document.getElementById(`price-${id}`).value);
    const available = document.getElementById(`avail-${id}`).value === "1";

    try {
        const res = await fetch('/api/admin/update-product', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify({ id, price, available })
        });
        if (res.ok) {
            alert('Updated!');
            fetchProducts();
        }
    } catch (e) {
        alert('Update failed.');
    }
}

// Global UI
function closeModals() {
    if (!userToken) {
        // Only allow closing other modals, not auth
        document.getElementById('cartModal').style.display = 'none';
        document.getElementById('adminModal').style.display = 'none';
        return;
    }
    document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
}

function showHome() {
    document.getElementById('productsSection').scrollIntoView({ behavior: 'smooth' });
}
