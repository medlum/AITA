from streamlit_chat import message
import streamlit as st
from utils_template import *
from utils_tts import *
import streamlit_antd_components as sac
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain_huggingface import HuggingFaceEndpoint
from langchain.chains import LLMChain
from huggingface_hub.errors import OverloadedError
import re
# from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler


# ---------set up page config -------------#
st.set_page_config(page_title="A.I.T.A",
                   layout="wide", page_icon="👾")

# ---- set up creative chat history ----#
chat_msg = StreamlitChatMessageHistory(key="chat_key")
chat_history_size = 5

# ---------set up LLM  -------------#
llama3p1_70B = "meta-llama/Meta-Llama-3.1-70B-Instruct"

# ---------set up general memory  -------------#
conversational_memory = ConversationBufferMemory(
    memory_key='chat_history',
    chat_memory=chat_msg,
    k=chat_history_size,
    return_messages=True
)

# ---------set up for creative mode  -------------#
# Initialize LLM for creative mode
# callbacks = [StreamingStdOutCallbackHandler()]
llm_creative = HuggingFaceEndpoint(
    repo_id=llama3p1_70B,
    task="text-generation",
    max_new_tokens=1000,
    do_sample=False,
    temperature=0.2,
    repetition_penalty=1.1,
    return_full_text=False,
    top_p=0.2,
    top_k=40,
    # streaming=True,
    # callbacks=callbacks,
    huggingfacehub_api_token=st.secrets["huggingfacehub_api_token"]
)

# ------ set up the llm chain -----#
chat_llm_chain = LLMChain(
    llm=llm_creative,
    prompt=chatPrompt,  # located at utils_prompt.py
    verbose=True,
    memory=conversational_memory,
)

# ------ initial welcome message -------#

# set up session state as a gate to display welcome message
if 'initial_msg' not in st.session_state:
    st.session_state.initial_msg = 0

# if 0, add welcome message to chat_msg
if st.session_state.initial_msg == 0:

    part_day = get_time_bucket()  # located at utils_tts.py
    welcome_msg = f"{part_day} {msg_template}"
    chat_msg.add_ai_message(welcome_msg)
# ------ set up message from chat history  -----#

for index, msg in enumerate(chat_msg.messages):

    # bot's message is in even position as welcome message is added at initial
    if index % 2 == 0:

        message(msg.content.replace('<|eot_id|>', '').replace("assistant", "").replace('Human:', ''),
                is_user=False,
                key=f"bot{index}",
                avatar_style="big-ears",
                seed="Salem",
                allow_html=True,
                is_table=True,)

    # user's message is in odd position
    else:
        edited_msg = msg.content
        edited_msg.replace('<|eot_id|>', '')
        human = re.search(r"Human:.*|human:.*", edited_msg)
        if human is not None:
            # exclude "Human:" located at end of string
            edited_msg = edited_msg[:human.start()]

        # message(msg.content.replace('<|eot_id|>', ''),
        #        is_user=True, key=f"user{index}",
        #        avatar_style="big-ears", seed="Angel")

    # -----clear history -----#
    # add a clear_btn
    clear_btn = sac.buttons([sac.ButtonsItem(icon=sac.BsIcon(name='x-circle', size=20))],
                            align='left',
                            variant='link',
                            index=None,
                            label=" ",
                            key=f"clear_msg{index}"
                            )

    # - clear chat_msg
    # - set initial_msg to 1 to stop welcome message
    if clear_btn is not None:
        chat_msg.messages.pop(-1)
        # chat_msg.clear()

    # set initial_msg to 0 in first loop
    if index == 0:
        st.session_state.initial_msg = 1

# -
if prompt := st.chat_input("Ask me a question..."):
    # show prompt message
    message(prompt,
            is_user=True,
            key=f"user",
            avatar_style="big-ears",
            seed="Angel")

    with st.spinner("Generating text and voice..."):

        try:

            # use {'human_input': f'{prompt}<|eot_id|>'})
            response = chat_llm_chain.invoke(
                {'human_input': f'{prompt}<|eot_id|>'})

            # remove prompt format for better display
            edited_response = response["text"].replace("assistant", "")
            human = re.search(r"Human:.*|human:.*", edited_response)
            if human is not None:
                # exclude "Human:" located at end of string
                edited_response = edited_response[:human.start()]

            # show message
            message(edited_response,
                    is_user=False,
                    key=f"bot_2",
                    avatar_style="big-ears",
                    seed="Salem",
                    allow_html=True,
                    is_table=True,)

            # st_copy_to_clipboard(edited_response)

            # audio conversation
            txt2speech(edited_response)
            col1, col2 = st.columns([1, 3])
            col1.audio("audio.mp3", autoplay=True, format="audio/mpeg")

        except OverloadedError as error:
            st.write(
                "HuggingFace🤗 inference engine is overloaded now. Try toggling to the creative mode in the meantime.")
