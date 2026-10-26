--
-- PostgreSQL database dump
--

\restrict YXobIxMVI33S7GvTHj1cmhNVy6Y8vrbty3iMyRJHkP9SKlDCXk9ZiUlI89hbnRw

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: countries; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.countries (id, name) FROM stdin;
1	Afghanistan
2	Albania
3	Algeria
4	Andorra
5	Angola
6	Antigua and Barbuda
7	Argentina
8	Armenia
9	Australia
10	Austria
11	Azerbaijan
12	Bahamas
13	Bahrain
14	Bangladesh
15	Barbados
16	Belarus
17	Belgium
18	Belize
19	Benin
20	Bhutan
21	Bolivia
22	Bosnia and Herzegovina
23	Botswana
24	Brazil
25	Brunei
26	Bulgaria
27	Burkina Faso
28	Burundi
29	Cabo Verde
30	Cambodia
31	Cameroon
32	Canada
33	Central African Republic
34	Chad
35	Chile
36	China
37	Colombia
38	Comoros
39	Congo
40	Costa Rica
41	Croatia
42	Cuba
43	Cyprus
44	Czechia
45	Democratic Republic of the Congo
46	Denmark
47	Djibouti
48	Dominica
49	Dominican Republic
50	Ecuador
51	Egypt
52	El Salvador
53	Equatorial Guinea
54	Eritrea
55	Estonia
56	Eswatini
57	Ethiopia
58	Fiji
59	Finland
60	France
61	Gabon
62	Gambia
63	Georgia
64	Germany
65	Ghana
66	Greece
67	Grenada
68	Guatemala
69	Guinea
70	Guinea-Bissau
71	Guyana
72	Haiti
73	Holy See
74	Honduras
75	Hungary
76	Iceland
77	India
78	Indonesia
79	Iran
80	Iraq
81	Ireland
82	Israel
83	Italy
84	Jamaica
85	Japan
86	Jordan
87	Kazakhstan
88	Kenya
89	Kiribati
90	Kuwait
91	Kyrgyzstan
92	Laos
93	Latvia
94	Lebanon
95	Lesotho
96	Liberia
97	Libya
98	Liechtenstein
99	Lithuania
100	Luxembourg
101	Madagascar
102	Malawi
103	Malaysia
104	Maldives
105	Mali
106	Malta
107	Marshall Islands
108	Mauritania
109	Mauritius
110	Mexico
111	Micronesia
112	Moldova
113	Monaco
114	Mongolia
115	Montenegro
116	Morocco
117	Mozambique
118	Myanmar
119	Namibia
120	Nauru
121	Nepal
122	Netherlands
123	New Zealand
124	Nicaragua
125	Niger
126	Nigeria
127	North Korea
128	North Macedonia
129	Norway
130	Oman
131	Pakistan
132	Palau
133	Palestine
134	Panama
135	Papua New Guinea
136	Paraguay
137	Peru
138	Philippines
139	Poland
140	Portugal
141	Qatar
142	Romania
143	Russia
144	Rwanda
145	Saint Kitts and Nevis
146	Saint Lucia
147	Saint Vincent and the Grenadines
148	Samoa
149	San Marino
150	Sao Tome and Principe
151	Saudi Arabia
152	Senegal
153	Serbia
154	Seychelles
155	Sierra Leone
156	Singapore
157	Slovakia
158	Slovenia
159	Solomon Islands
160	Somalia
161	South Africa
162	South Korea
163	South Sudan
164	Spain
165	Sri Lanka
166	Sudan
167	Suriname
168	Sweden
169	Switzerland
170	Syria
171	Tajikistan
172	Tanzania
173	Thailand
174	Timor-Leste
175	Togo
176	Tonga
177	Trinidad and Tobago
178	Tunisia
179	Turkey
180	Turkmenistan
181	Tuvalu
182	Uganda
183	Ukraine
184	United Arab Emirates
185	United Kingdom
186	United States
187	Uruguay
188	Uzbekistan
189	Vanuatu
190	Venezuela
191	Vietnam
192	Yemen
193	Zambia
194	Zimbabwe
195	Vatican City
\.


--
-- Data for Name: states; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.states (id, name, country_id) FROM stdin;
1	Andhra Pradesh	77
2	Arunachal Pradesh	77
3	Assam	77
4	Bihar	77
5	Chhattisgarh	77
6	Goa	77
7	Gujarat	77
8	Haryana	77
9	Himachal Pradesh	77
10	Jharkhand	77
11	Karnataka	77
12	Kerala	77
13	Madhya Pradesh	77
14	Maharashtra	77
15	Manipur	77
16	Meghalaya	77
17	Mizoram	77
18	Nagaland	77
19	Odisha	77
20	Punjab	77
21	Rajasthan	77
22	Sikkim	77
23	Tamil Nadu	77
24	Telangana	77
25	Tripura	77
26	Uttar Pradesh	77
27	Uttarakhand	77
28	West Bengal	77
29	Andaman and Nicobar Islands	77
30	Chandigarh	77
31	Dadra and Nagar Haveli and Daman and Diu	77
32	Delhi	77
33	Jammu and Kashmir	77
34	Ladakh	77
35	Lakshadweep	77
36	Puducherry	77
\.


--
-- Data for Name: districts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.districts (id, name, state_id) FROM stdin;
1	Ahmednagar	14
2	Akola	14
3	Amravati	14
4	Aurangabad	14
5	Beed	14
6	Bhandara	14
7	Buldhana	14
8	Chandrapur	14
9	Dhule	14
10	Gadchiroli	14
11	Gondia	14
12	Hingoli	14
13	Jalgaon	14
14	Jalna	14
15	Kolhapur	14
16	Latur	14
17	Mumbai City	14
18	Mumbai Suburban	14
19	Nagpur	14
20	Nanded	14
21	Nandurbar	14
22	Nashik	14
23	Osmanabad	14
24	Palghar	14
25	Parbhani	14
26	Pune	14
27	Raigad	14
28	Ratnagiri	14
29	Sangli	14
30	Satara	14
31	Sindhudurg	14
32	Solapur	14
33	Thane	14
34	Wardha	14
35	Washim	14
36	Yavatmal	14
\.


--
-- Data for Name: talukas; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.talukas (id, name, district_id) FROM stdin;
1	Miraj	29
2	Sangli	29
3	Tasgaon	29
4	Kavathe Mahankal	29
5	Jat	29
6	Atpadi	29
7	Khanapur	29
8	Palus	29
9	Kadegaon	29
10	Walwa	29
11	Ambegaon	26
12	Baramati	26
13	Bhor	26
14	Daund	26
15	Haveli	26
16	Indapur	26
17	Junnar	26
18	Khed	26
19	Mawal	26
20	Mulshi	26
21	Pune City	26
22	Purandhar	26
23	Shirur	26
24	Velhe	26
\.


--
-- Name: countries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.countries_id_seq', 1, false);


--
-- Name: districts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.districts_id_seq', 1, false);


--
-- Name: states_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.states_id_seq', 1, false);


--
-- Name: talukas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.talukas_id_seq', 1, true);


--
-- PostgreSQL database dump complete
--

\unrestrict YXobIxMVI33S7GvTHj1cmhNVy6Y8vrbty3iMyRJHkP9SKlDCXk9ZiUlI89hbnRw

