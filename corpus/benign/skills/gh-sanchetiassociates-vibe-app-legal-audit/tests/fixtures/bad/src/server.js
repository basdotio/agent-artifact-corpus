const sgMail = require('@sendgrid/mail');
const stripe = require('stripe')(process.env.KEY);
app.post('/launch', async () => { await sgMail.send({to, subject:'We launched!', html:'<p>Big launch announcement</p>'}); });
app.post('/pay', async () => stripe.checkout.sessions.create({mode:'subscription', line_items:[{price:'price_1'}]}));
app.post('/signup', (req,res)=>{ supabase.auth.signUp(req.body) });
