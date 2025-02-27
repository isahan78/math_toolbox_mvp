#!/usr/bin/env python3
"""
A minimal Streamlit UI that calls the multi_turn_virtual_tools.py 
multi-agent system to solve wordy math problems with 
unreliable sum/product and virtual tool caching.
"""
#%%
import streamlit as st
from multi_agent_toolbox import ask_system

def main():
    st.title("Multi-Agent Math System (Streamlit UI)")
    st.write("""
    This app uses a multi-turn LLM approach to discover tools 
    (without a single big prompt), executes a plan for your math question, 
    and eventually caches repeated solutions as 'virtual tools.'
    """)

    # Text input for user's wordy math question
    user_question = st.text_input("Enter a math question or scenario:", value="John has 3 apples, Mary has 5. Combine them, then multiply the total by 2.")

    if st.button("Solve"):
        with st.spinner("Thinking..."):
            result = ask_system(user_question)

        # Display result
        st.subheader("Result")
        if result["status"] == "success":
            st.write(f"**Answer:** {result['answer']}")
            st.write(f"**Plan:** {result['plan']}")
            st.write(f"**Via**: {result.get('via','?')}")
        else:
            st.error(f"Failed to solve: {result.get('error','Unknown error')}")
            st.write(f"Plan text: {result.get('plan','<none>')}")

    st.write("---")
    st.write("© 2023 Multi-turn Virtual Tools Demo")

if __name__ == "__main__":
    main()