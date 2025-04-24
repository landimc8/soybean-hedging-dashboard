{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 5,
   "id": "047aba8a-d597-4fef-9fcf-88ee1194b2a4",
   "metadata": {},
   "outputs": [
    {
     "name": "stderr",
     "output_type": "stream",
     "text": [
      "2025-04-24 10:33:50.135 \n",
      "  \u001b[33m\u001b[1mWarning:\u001b[0m to view this Streamlit app on a browser, run it with the following\n",
      "  command:\n",
      "\n",
      "    streamlit run /opt/anaconda3/lib/python3.12/site-packages/ipykernel_launcher.py [ARGUMENTS]\n",
      "2025-04-24 10:33:50.136 Session state does not function when running a script without `streamlit run`\n"
     ]
    }
   ],
   "source": [
    "import streamlit as st\n",
    "\n",
    "st.title(\"Hello Streamlit!\")\n",
    "\n",
    "name = st.text_input(\"Enter your name:\")\n",
    "\n",
    "if name:\n",
    "    st.write(f\"Hello, {name}!\")\n",
    "\n",
    "st.button(\"Click Me\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "98a9390e-d874-46c0-a1d2-6804f65d8df1",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "python312",
   "language": "python",
   "name": "python312"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.12.2"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
